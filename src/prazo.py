"""Regra única de cálculo do prazo do precatório."""

from datetime import date

from src.normalizacao import normalizar_data


def calcular_prazo(apresentado_em: str | date) -> date:
    """Calcula 31/12 do ano seguinte ou do segundo ano seguinte."""
    data = apresentado_em if isinstance(apresentado_em, date) else normalizar_data(apresentado_em)
    ano_vencimento = data.year + (1 if (data.month, data.day) <= (4, 2) else 2)
    return date(ano_vencimento, 12, 31)
