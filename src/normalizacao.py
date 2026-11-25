"""Padroniza números de processo, valores, nomes e datas."""

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation


FUSO_BRASIL = timezone(timedelta(hours=-3))


def normalizar_processo(valor: str) -> str:
    """Retorna os 20 dígitos do processo ou levanta ValueError."""
    if not isinstance(valor, str):
        raise ValueError("processo deve ser texto")
    texto = valor.strip()
    if not re.fullmatch(r"[0-9.\-\s]+", texto):
        raise ValueError("processo contém caracteres inválidos")
    digitos = re.sub(r"[.\-\s]", "", texto)
    if len(digitos) != 20:
        raise ValueError("processo deve conter exatamente 20 dígitos")
    return digitos


def formatar_processo(numero: str) -> str:
    """Formata 20 dígitos no padrão CNJ para exibição."""
    canonico = normalizar_processo(numero)
    return (
        f"{canonico[:7]}-{canonico[7:9]}.{canonico[9:13]}."
        f"{canonico[13]}.{canonico[14:16]}.{canonico[16:]}"
    )


def normalizar_valor(valor: object) -> Decimal:
    """Converte número ou texto brasileiro em Decimal, sem usar float."""
    if valor is None:
        raise ValueError("valor ausente")

    if isinstance(valor, Decimal):
        resultado = Decimal(str(valor))
    else:
        texto = str(valor).strip()
        if not texto:
            raise ValueError("valor ausente")
        if "," in texto:
            # No formato brasileiro, ponto separa milhares e vírgula decimais.
            texto = texto.replace(".", "").replace(",", ".")
        try:
            resultado = Decimal(str(texto))
        except InvalidOperation as erro:
            raise ValueError(f"valor inválido: {valor}") from erro

    if not resultado.is_finite():
        raise ValueError(f"valor inválido: {valor}")
    return resultado


def normalizar_nome_ente(nome: str) -> str:
    """Cria uma chave de comparação sem acentos, caixa ou espaços extras."""
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", nome)
        if not unicodedata.combining(caractere)
    )
    return " ".join(sem_acentos.casefold().split())


def normalizar_data(valor: str) -> date:
    """Converte data ISO, data brasileira ou data e hora para data local."""
    texto = valor.strip()
    if not texto:
        raise ValueError("data ausente")

    try:
        return date.fromisoformat(texto)
    except ValueError:
        pass

    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        pass

    # Python 3.10 não aceita Z em fromisoformat; troca pelo offset UTC.
    texto_iso = texto[:-1] + "+00:00" if texto.endswith("Z") else texto
    try:
        data_hora = datetime.fromisoformat(texto_iso)
    except ValueError as erro:
        raise ValueError(f"data inválida: {valor}") from erro

    if data_hora.tzinfo is None:
        raise ValueError("data e hora precisam informar o fuso")
    return data_hora.astimezone(FUSO_BRASIL).date()
