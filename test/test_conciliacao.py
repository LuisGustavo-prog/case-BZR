from pathlib import Path

from src.conciliacao import conciliar_precatorios
from src.leitura import ler_arquivos


def test_concilia_fontes_e_identifica_divergencias_reais():
    dados = ler_arquivos(Path("dados/entrada"))
    precatorios, problemas = conciliar_precatorios(
        dados["tribunal"], dados["hub"], dados["apresentacoes"]
    )
    por_numero = {p["numero_processo"]: p for p in precatorios}

    assert len(precatorios) == 6
    assert not problemas
    assert por_numero["00123451020198260053"]["prazo_pagamento"].isoformat() == "2026-12-31"
    assert por_numero["00234562120208260053"]["valor_face"] == 30000
    assert por_numero["00234562120208260053"]["situacao"] == "corrigido"
    assert por_numero["00456784320215020011"]["situacao"] == "em dúvida"
    assert por_numero["00567895420174036100"]["situacao"] == "em dúvida"
    assert por_numero["00678906520168260053"]["situacao"] == "corrigido"
