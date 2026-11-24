from datetime import date
from decimal import Decimal
from pathlib import Path

from src.conciliacao import conciliar_precatorios
from src.leitura import ler_arquivos
from src.pagamentos import processar_pagamentos


def test_pagamentos_reais_aplicam_status_e_removem_duplicata():
    dados = ler_arquivos(Path("dados/entrada"))
    precatorios, _ = conciliar_precatorios(
        dados["tribunal"], dados["hub"], dados["apresentacoes"]
    )
    pagamentos, ocorrencias = processar_pagamentos(dados["pagamentos"], precatorios)
    por_evento = {p["evento_id"]: p for p in pagamentos}

    assert len(pagamentos) == 11
    assert por_evento["ev-001"]["valor"] == Decimal("15500.0")
    assert por_evento["ev-001"]["situacao"] == "em dúvida"
    assert por_evento["ev-002"]["valor"] == Decimal("2500.50")
    assert por_evento["ev-002"]["situacao"] == "ok"
    assert por_evento["ev-004"]["situacao"] == "descartado"
    assert por_evento["ev-005"]["situacao"] == "corrigido"
    assert por_evento["ev-008"]["motivo"] == "precatório em dúvida"
    assert por_evento["ev-009"]["valor"] == Decimal("-200")
    assert por_evento["ev-009"]["situacao"] == "em dúvida"
    assert por_evento["ev-010"]["situacao"] == "descartado"
    assert por_evento["ev-011"]["situacao"] == "corrigido"
    assert any("registro 4" in item["evidencia"] for item in ocorrencias)


def test_versao_antiga_que_chega_depois_nao_substitui_a_nova():
    linhas = [
        {
            "_registro": 1,
            "evento_id": "ev-x",
            "processo": "0012345-10.2019.8.26.0053",
            "valor": Decimal("20"),
            "data_pagamento": "2025-05-01",
            "tipo": "pagamento",
            "atualizado_em": "2025-05-02T10:00:00-03:00",
        },
        {
            "_registro": 2,
            "evento_id": "ev-x",
            "processo": "0012345-10.2019.8.26.0053",
            "valor": Decimal("10"),
            "data_pagamento": "2025-05-01",
            "tipo": "pagamento",
            "atualizado_em": "2025-05-01T10:00:00-03:00",
        },
    ]
    precatorios = [{
        "numero_processo": "00123451020198260053",
        "situacao": "ok",
        "apresentado_em": date(2025, 4, 2),
    }]

    pagamentos, _ = processar_pagamentos(linhas, precatorios)

    assert len(pagamentos) == 1
    assert pagamentos[0]["valor"] == Decimal("20")
    assert pagamentos[0]["situacao"] == "corrigido"
