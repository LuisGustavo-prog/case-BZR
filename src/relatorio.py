"""Calcula os totais e grava as planilhas e o relatório da limpeza."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any


def _dinheiro(valor: Decimal | None) -> str:
    return "" if valor is None else f"{valor:.2f}"


def _data(valor: Any) -> str:
    return "" if valor is None else valor.isoformat()


def _valor_assinado_pagamento(pagamento: dict[str, Any]) -> Decimal | None:
    valor = pagamento["valor"]
    if valor is None:
        return None
    if pagamento["tipo"] == "estorno" and valor > 0:
        return -valor
    return valor


def preparar_saidas(
    precatorios: list[dict[str, Any]],
    pagamentos: list[dict[str, Any]],
    ocorrencias: list[dict[str, Any]],
    total_lidos: int,
) -> dict[str, Any]:
    """Prepara linhas dos arquivos de saída e o texto do relatório."""
    pagamentos_por_processo: dict[str, list[dict[str, Any]]] = {}
    for pagamento in pagamentos:
        pagamentos_por_processo.setdefault(pagamento["numero_processo"], []).append(pagamento)

    precatorios_limpos: list[dict[str, str]] = []
    pagamentos_limpos: list[dict[str, str]] = []
    fora: list[dict[str, str]] = []
    totais: dict[str, Decimal] = {}
    pendentes: dict[str, Decimal] = {}

    for precatorio in precatorios:
        numero = precatorio["numero_processo"]
        confiaveis = [
            pagamento
            for pagamento in pagamentos_por_processo.get(numero, [])
            if pagamento["situacao"] in ("ok", "corrigido")
        ]
        total = sum(
            (
                pagamento["valor"]
                if pagamento["tipo"] == "pagamento"
                else -pagamento["valor"]
                for pagamento in confiaveis
                if pagamento["valor"] is not None
            ),
            Decimal("0"),
        )
        totais[numero] = total

        eventos_pendentes = [
            pagamento
            for pagamento in pagamentos_por_processo.get(numero, [])
            if pagamento["situacao"] == "em dúvida"
        ]
        pendentes[numero] = sum(
            (valor for pagamento in eventos_pendentes
             if (valor := _valor_assinado_pagamento(pagamento)) is not None),
            Decimal("0"),
        )

        if precatorio["situacao"] in ("ok", "corrigido"):
            precatorios_limpos.append({
                "numero_processo": numero,
                "numero_formatado": precatorio["numero_formatado"],
                "ente_devedor": precatorio["ente_devedor"],
                "valor_face": _dinheiro(precatorio["valor_face"]),
                "apresentado_em": _data(precatorio["apresentado_em"]),
                "prazo_pagamento": _data(precatorio["prazo_pagamento"]),
                "total_pago": _dinheiro(total),
                "situacao": precatorio["situacao"],
                "observacao": precatorio["motivo"],
            })
        else:
            fora.append({
                "tipo_item": "precatorio",
                "identificador": numero,
                "situacao": precatorio["situacao"],
                "motivo": precatorio["motivo"],
                "evidencia": precatorio["evidencia"],
                "valor_pendente": "",
            })

        for pagamento in pagamentos_por_processo.get(numero, []):
            if pagamento["situacao"] in ("ok", "corrigido") and precatorio["situacao"] in ("ok", "corrigido"):
                pagamentos_limpos.append({
                    "evento_id": pagamento["evento_id"],
                    "numero_processo": numero,
                    "tipo": pagamento["tipo"],
                    "valor": _dinheiro(pagamento["valor"]),
                    "pago_em": _data(pagamento["pago_em"]),
                    "atualizado_em": pagamento["atualizado_em"],
                    "situacao": pagamento["situacao"],
                    "motivo": pagamento["motivo"],
                    "registro_origem": str(pagamento["registro_origem"]),
                })

    for pagamento in pagamentos:
        if pagamento["situacao"] in ("em dúvida", "descartado"):
            valor_pendente = _valor_assinado_pagamento(pagamento)
            fora.append({
                "tipo_item": "pagamento",
                "identificador": pagamento["evento_id"] or f"registro {pagamento['registro_origem']}",
                "situacao": pagamento["situacao"],
                "motivo": pagamento["motivo"],
                "evidencia": pagamento["evidencia"],
                "valor_pendente": _dinheiro(valor_pendente),
            })

    for ocorrencia in ocorrencias:
        if ocorrencia["situacao"] in ("em dúvida", "descartado"):
            fora.append({
                "tipo_item": ocorrencia["tipo_item"],
                "identificador": ocorrencia["identificador"],
                "situacao": ocorrencia["situacao"],
                "motivo": ocorrencia["motivo"],
                "evidencia": ocorrencia["evidencia"],
                "valor_pendente": _dinheiro(ocorrencia["valor_pendente"]),
            })

    precatorios_limpos.sort(key=lambda linha: linha["numero_processo"])
    pagamentos_limpos.sort(key=lambda linha: (linha["numero_processo"], int(linha["registro_origem"])))
    fora.sort(key=lambda linha: (linha["identificador"], linha["tipo_item"], linha["evidencia"]))

    itens_finalizados = precatorios + pagamentos
    contagens = {
        situacao: sum(item["situacao"] == situacao for item in itens_finalizados)
        for situacao in ("ok", "corrigido", "em dúvida", "descartado")
    }
    correcoes = [
        item for item in (
            [
                {
                    "tipo_item": "precatorio",
                    "identificador": p["numero_processo"],
                    "situacao": p["situacao"],
                    "motivo": p["motivo"],
                    "evidencia": p["evidencia"],
                }
                for p in precatorios if p["situacao"] == "corrigido"
            ]
            + [
                {
                    "tipo_item": "pagamento",
                    "identificador": p["evento_id"] or f"registro {p['registro_origem']}",
                    "situacao": p["situacao"],
                    "motivo": p["motivo"],
                    "evidencia": p["evidencia"],
                }
                for p in pagamentos if p["situacao"] == "corrigido"
            ]
            + [o for o in ocorrencias if o["situacao"] == "corrigido"]
        )
    ]
    duvidas = [
        item for item in (
            [
                {
                    "tipo_item": "precatorio",
                    "identificador": p["numero_processo"],
                    "situacao": p["situacao"],
                    "motivo": p["motivo"],
                    "evidencia": p["evidencia"],
                }
                for p in precatorios if p["situacao"] == "em dúvida"
            ]
            + [
                {
                    "tipo_item": "pagamento",
                    "identificador": p["evento_id"] or f"registro {p['registro_origem']}",
                    "situacao": p["situacao"],
                    "motivo": p["motivo"],
                    "evidencia": p["evidencia"],
                }
                for p in pagamentos if p["situacao"] == "em dúvida"
            ]
            + [o for o in ocorrencias if o["situacao"] == "em dúvida"]
        )
    ]
    descartados = [
        {
            "tipo_item": "pagamento",
            "identificador": p["evento_id"] or f"registro {p['registro_origem']}",
            "situacao": p["situacao"],
            "motivo": p["motivo"],
            "evidencia": p["evidencia"],
        }
        for p in pagamentos if p["situacao"] == "descartado"
    ]

    divergencias = [
        (p["numero_processo"], texto, p["evidencia"])
        for p in precatorios for texto in p["divergencias"]
    ]
    prazos_diferentes = [
        p for p in precatorios if p["prazo_hub_diferente"]
    ]

    linhas_md = [
        "# Relatório da limpeza de precatórios",
        "",
        f"Registros lidos nas fontes: **{total_lidos}**. Precatórios conciliados: **{len(precatorios)}**. "
        f"Eventos consolidados: **{len(pagamentos)}**.",
        "",
        "| Situação final | Precatórios e eventos |",
        "|---|---:|",
    ]
    for situacao, rotulo in (
        ("ok", "ok"), ("corrigido", "corrigidos"),
        ("em dúvida", "em dúvida"), ("descartado", "descartados"),
    ):
        linhas_md.append(f"| {rotulo} | {contagens[situacao]} |")

    for titulo, itens in (("Corrigido", correcoes), ("Em dúvida", duvidas), ("Descartado", descartados)):
        linhas_md.extend(["", f"## {titulo}", ""])
        if not itens:
            linhas_md.append("Nenhum caso.")
            continue
        for item in itens:
            linhas_md.append(
                f"- **{item['tipo_item']} {item['identificador']}** — {item['motivo']}. "
                f"Evidência: {item['evidencia']}."
            )

    linhas_md.extend(["", "## Divergências entre tribunal e hub", ""])
    if divergencias:
        for numero, texto, evidencia in divergencias:
            linhas_md.append(f"- **{numero}** — {texto}. Evidência: {evidencia}.")
    else:
        linhas_md.append("Nenhuma divergência encontrada.")

    linhas_md.extend(["", "## Prazos do hub diferentes do prazo calculado", ""])
    if prazos_diferentes:
        for precatorio in prazos_diferentes:
            linhas_md.append(
                f"- **{precatorio['numero_processo']}** — hub {_data(precatorio['prazo_hub'])}; "
                f"calculado {_data(precatorio['prazo_pagamento'])}. Evidência: {precatorio['evidencia']}."
            )
    else:
        linhas_md.append("Nenhuma divergência de prazo encontrada.")

    linhas_md.extend([
        "", "## Totais por processo", "",
        "| Processo | Situação do precatório | Total confiável | Valor pendente em dúvida |",
        "|---|---|---:|---:|",
    ])
    for precatorio in precatorios:
        numero = precatorio["numero_processo"]
        linhas_md.append(
            f"| {numero} | {precatorio['situacao']} | {_dinheiro(totais.get(numero, Decimal('0')))} | "
            f"{_dinheiro(pendentes.get(numero, Decimal('0')))} |"
        )

    return {
        "precatorios_limpos": precatorios_limpos,
        "pagamentos_limpos": pagamentos_limpos,
        "fora_da_base": fora,
        "relatorio_md": "\n".join(linhas_md) + "\n",
    }


def _gravar_csv(caminho: Path, colunas: list[str], linhas: list[dict[str, str]]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=colunas,
            extrasaction="ignore",
            lineterminator="\n",
        )
        escritor.writeheader()
        escritor.writerows(linhas)


def gravar_saidas(saida: Path, resultados: dict[str, Any]) -> None:
    """Grava apenas dentro do diretório indicado como saída."""
    saida.mkdir(parents=True, exist_ok=True)
    _gravar_csv(
        saida / "precatorios_limpos.csv",
        ["numero_processo", "numero_formatado", "ente_devedor", "valor_face",
         "apresentado_em", "prazo_pagamento", "total_pago", "situacao", "observacao"],
        resultados["precatorios_limpos"],
    )
    _gravar_csv(
        saida / "pagamentos_limpos.csv",
        ["evento_id", "numero_processo", "tipo", "valor", "pago_em",
         "atualizado_em", "situacao", "motivo", "registro_origem"],
        resultados["pagamentos_limpos"],
    )
    _gravar_csv(
        saida / "fora_da_base.csv",
        ["tipo_item", "identificador", "situacao", "motivo", "evidencia", "valor_pendente"],
        resultados["fora_da_base"],
    )
    (saida / "relatorio.md").write_text(
        resultados["relatorio_md"], encoding="utf-8", newline="\n"
    )
    
