from datetime import date
from decimal import Decimal

import pytest

from src.normalizacao import (
    formatar_processo,
    normalizar_data,
    normalizar_nome_ente,
    normalizar_processo,
    normalizar_valor,
)


PROCESSO_FORMATADO = "0012345-10.2019.8.26.0053"
PROCESSO_CANONICO = "00123451020198260053"


def test_normaliza_processo_formatado_e_sem_pontuacao():
    assert normalizar_processo(PROCESSO_FORMATADO) == PROCESSO_CANONICO
    assert normalizar_processo(PROCESSO_CANONICO) == PROCESSO_CANONICO
    assert formatar_processo(PROCESSO_CANONICO) == PROCESSO_FORMATADO


def test_rejeita_processo_com_formato_invalido():
    with pytest.raises(ValueError):
        normalizar_processo("processo-inválido")


def test_normaliza_valores_sem_float():
    assert normalizar_valor("2.500,50") == Decimal("2500.50")
    assert normalizar_valor(Decimal("45000.00")) == Decimal("45000.00")


def test_normaliza_nome_ignorando_acentos_caixa_e_espacos():
    assert normalizar_nome_ente("  Município   de São Paulo ") == "municipio de sao paulo"
    assert normalizar_nome_ente("MUNICIPIO DE SAO PAULO") == "municipio de sao paulo"


def test_normaliza_datas_e_fuso_brasilia():
    assert normalizar_data("2025-04-02") == date(2025, 4, 2)
    assert normalizar_data("10/04/2025") == date(2025, 4, 10)
    assert normalizar_data("2025-04-03T01:00:00Z") == date(2025, 4, 2)
