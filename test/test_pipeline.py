import csv
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from src.limpeza import executar


ENTRADA = Path("dados/entrada")


def _hash_arquivos(diretorio: Path) -> dict[str, str]:
    return {
        caminho.name: hashlib.sha256(caminho.read_bytes()).hexdigest()
        for caminho in sorted(diretorio.iterdir())
        if caminho.is_file()
    }


def test_pipeline_produz_base_esperada_sem_alterar_entradas():
    hashes_antes = _hash_arquivos(ENTRADA)
    with TemporaryDirectory() as temporario:
        saida = Path(temporario) / "saida"
        executar(ENTRADA, saida)

        with (saida / "precatorios_limpos.csv").open(encoding="utf-8", newline="") as arquivo:
            precatorios = list(csv.DictReader(arquivo))
        por_numero = {p["numero_processo"]: p for p in precatorios}
        assert len(precatorios) == 4
        assert por_numero["00123451020198260053"]["valor_face"] == "45000.00"
        assert por_numero["00123451020198260053"]["prazo_pagamento"] == "2026-12-31"
        assert por_numero["00123451020198260053"]["total_pago"] == "2500.50"
        assert por_numero["00234562120208260053"]["total_pago"] == "9200.00"
        assert por_numero["00345673220188260405"]["total_pago"] == "0.00"
        assert por_numero["00678906520168260053"]["total_pago"] == "4000.00"

        with (saida / "pagamentos_limpos.csv").open(encoding="utf-8", newline="") as arquivo:
            pagamentos = list(csv.DictReader(arquivo))
        assert {p["evento_id"] for p in pagamentos} == {
            "ev-002", "ev-003", "ev-005", "ev-006", "ev-007", "ev-011"
        }

        with (saida / "fora_da_base.csv").open(encoding="utf-8", newline="") as arquivo:
            fora = list(csv.DictReader(arquivo))
        assert not any(
            item["situacao"] in ("em dúvida", "descartado")
            and item["tipo_item"] == "pagamento"
            and item["identificador"] in {p["evento_id"] for p in pagamentos}
            for item in fora
        )

        relatorio = (saida / "relatorio.md").read_text(encoding="utf-8")
        assert "00123451020198260053" in relatorio
        assert "2027-12-31" in relatorio

        hashes_saida_antes = _hash_arquivos(saida)
        executar(ENTRADA, saida)
        assert _hash_arquivos(saida) == hashes_saida_antes

    assert _hash_arquivos(ENTRADA) == hashes_antes
