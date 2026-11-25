"""Lê os arquivos de entrada e guarda a posição de cada registro."""

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _ler_csv(
    caminho: Path,
    *,
    encoding: str,
    delimitador: str,
) -> list[dict[str, Any]]:
    """Lê um CSV e anexa o número da linha física de cada registro."""
    linhas: list[dict[str, Any]] = []
    with caminho.open("r", encoding=encoding, newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=delimitador)
        for linha in leitor:
            linha["_registro"] = leitor.line_num
            linhas.append(linha)
    return linhas


def ler_tribunal(entrada: Path) -> list[dict[str, Any]]:
    """Lê o arquivo do tribunal no formato recebido (Latin-1 e ponto e vírgula)."""
    return _ler_csv(
        entrada / "tribunal.csv",
        encoding="iso-8859-1",
        delimitador=";",
    )


def ler_hub(entrada: Path) -> list[dict[str, Any]]:
    """Lê a exportação do sistema em UTF-8 e separada por vírgulas."""
    return _ler_csv(
        entrada / "hub.csv",
        encoding="utf-8",
        delimitador=",",
    )


def _ler_json(caminho: Path) -> list[dict[str, Any]]:
    """Lê uma lista JSON e conserva a posição original, começando em 1."""
    with caminho.open("r", encoding="utf-8") as arquivo:
        registros = json.load(arquivo, parse_float=Decimal, parse_int=Decimal)

    if not isinstance(registros, list):
        raise ValueError(f"Esperava uma lista JSON em {caminho.name}")

    linhas: list[dict[str, Any]] = []
    for posicao, registro in enumerate(registros, start=1):
        if not isinstance(registro, dict):
            raise ValueError(
                f"Esperava um objeto no registro {posicao} de {caminho.name}"
            )
        linha = dict(registro)
        linha["_registro"] = posicao
        linhas.append(linha)
    return linhas


def ler_apresentacoes(entrada: Path) -> list[dict[str, Any]]:
    """Lê as datas de apresentação e conserva a posição no arquivo."""
    return _ler_json(entrada / "apresentacoes.json")


def ler_pagamentos(entrada: Path) -> list[dict[str, Any]]:
    """Lê pagamentos sem converter os campos de negócio nesta etapa."""
    return _ler_json(entrada / "pagamentos.json")


def ler_arquivos(entrada: Path) -> dict[str, list[dict[str, Any]]]:
    """Lê todas as fontes usadas pela limpeza."""
    return {
        "tribunal": ler_tribunal(entrada),
        "hub": ler_hub(entrada),
        "apresentacoes": ler_apresentacoes(entrada),
        "pagamentos": ler_pagamentos(entrada),
    }
