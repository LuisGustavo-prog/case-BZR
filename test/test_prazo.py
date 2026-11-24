from datetime import date

from src.prazo import calcular_prazo


def test_prazo_dia_2_de_abril_e_inclusivo():
    assert calcular_prazo("2025-04-02") == date(2026, 12, 31)


def test_prazo_depois_de_2_de_abril():
    assert calcular_prazo("2025-04-03") == date(2027, 12, 31)


def test_prazo_ano_bissexto():
    assert calcular_prazo("2024-02-29") == date(2025, 12, 31)


def test_prazo_converte_instante_para_fuso_brasil():
    assert calcular_prazo("2025-04-03T01:00:00Z") == date(2026, 12, 31)
    assert calcular_prazo("2025-04-02T23:30:00-03:00") == date(2026, 12, 31)
