"""Confere os pagamentos, remove duplicatas e escolhe a versão mais recente."""

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any

from src.normalizacao import normalizar_data, normalizar_processo, normalizar_valor


def _instante_atualizacao(valor: str) -> datetime:
    texto = valor.strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    instante = datetime.fromisoformat(texto)
    if instante.tzinfo is None:
        raise ValueError("atualizado_em precisa informar o fuso")
    return instante.astimezone(timezone.utc)


def _conteudo_sem_posicao(linha: dict[str, Any]) -> dict[str, Any]:
    return {chave: valor for chave, valor in linha.items() if chave != "_registro"}


def processar_pagamentos(
    linhas: list[dict[str, Any]],
    precatorios: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna eventos efetivos e ocorrências de versão/duplicação."""
    por_processo = {p["numero_processo"]: p for p in precatorios}
    grupos: dict[str, list[dict[str, Any]]] = {}
    for linha in linhas:
        evento_id = str(linha.get("evento_id") or "").strip()
        chave = evento_id if evento_id else f"__sem_id_{linha['_registro']}"
        grupos.setdefault(chave, []).append(linha)

    pagamentos: list[dict[str, Any]] = []
    ocorrencias: list[dict[str, Any]] = []

    for chave in sorted(grupos, key=lambda item: min(r["_registro"] for r in grupos[item])):
        grupo = sorted(grupos[chave], key=lambda item: item["_registro"])
        evento_id = "" if chave.startswith("__sem_id_") else chave

        # Remove cópias exatas antes de escolher entre versões diferentes.
        versoes: list[dict[str, Any]] = []
        for linha in grupo:
            if any(_conteudo_sem_posicao(linha) == _conteudo_sem_posicao(v) for v in versoes):
                ocorrencias.append({
                    "tipo_item": "pagamento",
                    "identificador": evento_id or f"registro {linha['_registro']}",
                    "situacao": "corrigido",
                    "motivo": "registro duplicado idêntico; mantida uma cópia",
                    "evidencia": f"pagamentos.json, registro {linha['_registro']}",
                    "valor_pendente": Decimal("0"),
                })
            else:
                versoes.append(linha)

        versao_corrigida = len(versoes) > 1
        selecionada = versoes[0]
        problema_versao = ""
        if versao_corrigida:
            instantes: list[tuple[datetime, dict[str, Any]]] = []
            try:
                instantes = [
                    (_instante_atualizacao(str(v["atualizado_em"])), v)
                    for v in versoes
                ]
            except (KeyError, TypeError, ValueError):
                problema_versao = "versões diferentes sem atualizado_em válido"
            if instantes:
                mais_novo = max(instante for instante, _ in instantes)
                vencedoras = [v for instante, v in instantes if instante == mais_novo]
                if len(vencedoras) > 1:
                    problema_versao = "versões diferentes empatam em atualizado_em"
                else:
                    selecionada = vencedoras[0]
            ocorrencias.append({
                "tipo_item": "pagamento",
                "identificador": evento_id or f"registro {selecionada['_registro']}",
                "situacao": "corrigido" if not problema_versao else "em dúvida",
                "motivo": (
                    "versões diferentes; mantida a de atualizado_em mais recente"
                    if not problema_versao else problema_versao
                ),
                "evidencia": "; ".join(
                    f"pagamentos.json, registro {v['_registro']}" for v in versoes
                ),
                "valor_pendente": Decimal("0"),
            })

        registro = selecionada["_registro"]
        evidencia = f"pagamentos.json, registro {registro}"
        # Cada regra apenas marca o que encontrou. A situação final sai da
        # prioridade descartado > em dúvida > corrigido > ok, e nenhum motivo
        # é sobrescrito por outra regra.
        motivos: list[str] = []
        descartado = False
        em_duvida = False
        corrigido = versao_corrigida
        numero_processo = ""
        valor: Decimal | None = None
        pago_em = None

        processo_original = str(selecionada.get("processo") or "").strip()
        if not processo_original:
            descartado = True
            motivos.append("processo vazio; sem dados suficientes")
        else:
            try:
                numero_processo = normalizar_processo(processo_original)
            except ValueError:
                em_duvida = True
                motivos.append("número do processo inválido")
            else:
                if re.fullmatch(r"[0-9]{20}", processo_original):
                    corrigido = True
                    motivos.append("processo normalizado para 20 dígitos")

        valor_original = selecionada.get("valor")
        if valor_original is None:
            descartado = True
            motivos.append("valor nulo; sem dados suficientes")
        else:
            try:
                valor = normalizar_valor(valor_original)
            except ValueError as erro:
                em_duvida = True
                motivos.append(f"valor inválido: {erro}")
            else:
                if valor < 0:
                    em_duvida = True
                    motivos.append("valor negativo; pode ser estorno enviado incorretamente")

        tipo = str(selecionada.get("tipo") or "").strip().casefold()
        if tipo not in ("pagamento", "estorno"):
            em_duvida = True
            motivos.append(f"tipo de evento desconhecido: {tipo or 'vazio'}")

        try:
            pago_em = normalizar_data(str(selecionada.get("data_pagamento") or ""))
        except ValueError as erro:
            em_duvida = True
            motivos.append(f"data_pagamento inválida: {erro}")

        if problema_versao:
            em_duvida = True
            motivos.append(problema_versao)

        # Sem número de processo válido não há precatório para consultar.
        if numero_processo:
            precatorio = por_processo.get(numero_processo)
            if precatorio is None:
                em_duvida = True
                motivos.append("processo não existe em nenhuma fonte")
            else:
                if precatorio["situacao"] == "em dúvida":
                    em_duvida = True
                    motivos.append("precatório em dúvida")
                if precatorio.get("inclusao_tribunal"):
                    corrigido = True
                    motivos.append("precatório incluído a partir do tribunal")
                if (
                    pago_em
                    and precatorio.get("apresentado_em")
                    and pago_em < precatorio["apresentado_em"]
                ):
                    em_duvida = True
                    motivos.append("pagamento anterior à data de apresentação")

        if descartado:
            situacao = "descartado"
        elif em_duvida:
            situacao = "em dúvida"
        elif corrigido:
            situacao = "corrigido"
        else:
            situacao = "ok"
        motivo = "; ".join(dict.fromkeys(motivos))

        pagamentos.append({
            "evento_id": evento_id,
            "numero_processo": numero_processo,
            "tipo": tipo,
            "valor": valor,
            "pago_em": pago_em,
            "atualizado_em": str(selecionada.get("atualizado_em") or ""),
            "situacao": situacao,
            "motivo": motivo,
            "registro_origem": registro,
            "evidencia": evidencia,
            "versao_corrigida": versao_corrigida,
        })

    pagamentos.sort(key=lambda item: (item["numero_processo"], item["registro_origem"]))
    return pagamentos, ocorrencias
