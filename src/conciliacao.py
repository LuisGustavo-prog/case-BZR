"""Concilia a lista de precatórios do tribunal, do hub e das apresentações."""

from datetime import date
from decimal import Decimal
from typing import Any

from src.normalizacao import (
    formatar_processo,
    normalizar_data,
    normalizar_nome_ente,
    normalizar_processo,
    normalizar_valor,
)
from src.prazo import calcular_prazo


def _agrupar_por_processo(
    linhas: list[dict[str, Any]], campo_processo: str
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    agrupadas: dict[str, list[dict[str, Any]]] = {}
    invalidas: list[dict[str, Any]] = []
    for linha in linhas:
        try:
            numero = normalizar_processo(linha.get(campo_processo, ""))
        except (TypeError, ValueError):
            invalidas.append(linha)
            continue
        agrupadas.setdefault(numero, []).append(linha)
    return agrupadas, invalidas


def _evidencia(fonte: str, linha: dict[str, Any]) -> str:
    return f"{fonte}, registro/linha {linha['_registro']}"


def conciliar_precatorios(
    tribunal: list[dict[str, Any]],
    hub: list[dict[str, Any]],
    apresentacoes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna precatórios conciliados e ocorrências sem chave válida."""
    por_fonte = {
        "tribunal": _agrupar_por_processo(tribunal, "numero_processo"),
        "hub": _agrupar_por_processo(hub, "processo"),
        "apresentacoes": _agrupar_por_processo(apresentacoes, "processo"),
    }
    tribunal_por_numero, tribunal_invalidos = por_fonte["tribunal"]
    hub_por_numero, hub_invalidos = por_fonte["hub"]
    apresentacoes_por_numero, apresentacoes_invalidas = por_fonte["apresentacoes"]

    problemas: list[dict[str, Any]] = []
    for fonte, linhas in (
        ("tribunal.csv", tribunal_invalidos),
        ("hub.csv", hub_invalidos),
        ("apresentacoes.json", apresentacoes_invalidas),
    ):
        for linha in linhas:
            problemas.append({
                "tipo_item": "precatorio",
                "identificador": linha.get("numero_processo", linha.get("processo", "")),
                "situacao": "em dúvida",
                "motivo": "número do processo inválido ou ausente",
                "evidencia": _evidencia(fonte, linha),
                "valor_pendente": Decimal("0"),
            })

    todos = sorted(
        set(tribunal_por_numero) | set(hub_por_numero) | set(apresentacoes_por_numero)
    )
    conciliados: list[dict[str, Any]] = []

    for numero in todos:
        linhas_tribunal = tribunal_por_numero.get(numero, [])
        linhas_hub = hub_por_numero.get(numero, [])
        linhas_apresentacao = apresentacoes_por_numero.get(numero, [])
        evidencias: list[str] = []
        if linhas_tribunal:
            evidencias.append(_evidencia("tribunal.csv", linhas_tribunal[0]))
        if linhas_hub:
            evidencias.append(_evidencia("hub.csv", linhas_hub[0]))
        if linhas_apresentacao:
            evidencias.append(_evidencia("apresentacoes.json", linhas_apresentacao[0]))

        situacao = "ok"
        motivos: list[str] = []
        divergencias: list[str] = []
        valor_face: Decimal | None = None
        ente_devedor = ""

        if any(len(grupo) > 1 for grupo in (linhas_tribunal, linhas_hub, linhas_apresentacao)):
            situacao = "em dúvida"
            motivos.append("processo repetido em uma ou mais fontes")

        if linhas_tribunal and linhas_hub:
            dado_tribunal = linhas_tribunal[0]
            dado_hub = linhas_hub[0]
            ente_devedor = dado_tribunal["ente_devedor"].strip()
            try:
                valor_tribunal = normalizar_valor(dado_tribunal["valor_face"])
                valor_hub = normalizar_valor(dado_hub["valor_face"])
                valor_face = valor_tribunal
                if valor_tribunal != valor_hub:
                    divergencias.append(
                        f"valor de face: tribunal {valor_tribunal:.2f}; hub {valor_hub:.2f}"
                    )
                    if situacao != "em dúvida":
                        situacao = "corrigido"
                    motivos.append("valor de face do tribunal prevalece")
            except (KeyError, ValueError) as erro:
                situacao = "em dúvida"
                motivos.append(f"valor de face inválido: {erro}")

            ente_hub = dado_hub.get("ente", "").strip()
            if normalizar_nome_ente(ente_devedor) != normalizar_nome_ente(ente_hub):
                divergencias.append(f"ente devedor: tribunal {ente_devedor}; hub {ente_hub}")
                situacao = "em dúvida"
                motivos.append("ente devedor diverge entre tribunal e hub")
            elif ente_devedor != ente_hub:
                divergencias.append(f"grafia do ente: tribunal {ente_devedor}; hub {ente_hub}")
                if situacao == "ok":
                    situacao = "corrigido"
                motivos.append("grafia do tribunal prevalece")
        elif linhas_tribunal:
            dado_tribunal = linhas_tribunal[0]
            ente_devedor = dado_tribunal.get("ente_devedor", "").strip()
            try:
                valor_face = normalizar_valor(dado_tribunal["valor_face"])
            except (KeyError, ValueError) as erro:
                situacao = "em dúvida"
                motivos.append(f"valor de face inválido: {erro}")
            else:
                situacao = "corrigido"
                motivos.append("incluído a partir do tribunal")
        elif linhas_hub:
            dado_hub = linhas_hub[0]
            ente_devedor = dado_hub.get("ente", "").strip()
            try:
                valor_face = normalizar_valor(dado_hub["valor_face"])
            except (KeyError, ValueError) as erro:
                motivos.append(f"valor de face inválido: {erro}")
            situacao = "em dúvida"
            motivos.append("processo consta só no hub")
        else:
            situacao = "em dúvida"
            motivos.append("processo consta só em apresentacoes.json")

        data_apresentacao: date | None = None
        fonte_data = ""
        # O arquivo dedicado de apresentações é a fonte específica para esta data.
        if linhas_apresentacao:
            valor_data = linhas_apresentacao[0].get("apresentado_em", "")
            fonte_data = "apresentacoes.json"
            linha_data = linhas_apresentacao[0]
        elif linhas_hub:
            valor_data = linhas_hub[0].get("apresentado_em", "")
            fonte_data = "hub.csv"
            linha_data = linhas_hub[0]
        else:
            valor_data = ""
            linha_data = None

        if valor_data:
            try:
                data_apresentacao = normalizar_data(valor_data)
            except ValueError as erro:
                situacao = "em dúvida"
                motivos.append(f"data de apresentação inválida: {erro}")
                evidencias.append(_evidencia(fonte_data, linha_data))
        else:
            situacao = "em dúvida"
            motivos.append("data de apresentação ausente")

        prazo = calcular_prazo(data_apresentacao) if data_apresentacao else None
        prazo_hub: date | None = None
        if linhas_hub and linhas_hub[0].get("prazo_pagamento"):
            try:
                prazo_hub = normalizar_data(linhas_hub[0]["prazo_pagamento"])
            except ValueError:
                divergencias.append("prazo_pagamento do hub tem formato inválido")
            if prazo and prazo_hub and prazo != prazo_hub:
                divergencias.append(
                    f"prazo: calculado {prazo.isoformat()}; hub {prazo_hub.isoformat()}"
                )

        conciliados.append({
            "numero_processo": numero,
            "numero_formatado": formatar_processo(numero),
            "ente_devedor": ente_devedor,
            "valor_face": valor_face,
            "apresentado_em": data_apresentacao,
            "prazo_pagamento": prazo,
            "prazo_hub": prazo_hub,
            "prazo_hub_diferente": bool(prazo and prazo_hub and prazo != prazo_hub),
            "situacao": situacao,
            "inclusao_tribunal": bool(linhas_tribunal and not linhas_hub),
            "motivo": "; ".join(dict.fromkeys(motivos)),
            "evidencia": "; ".join(evidencias),
            "divergencias": divergencias,
        })

    return conciliados, problemas
