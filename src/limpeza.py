"""Inicia a limpeza e organiza as etapas do programa."""

import argparse
import logging
from pathlib import Path
from typing import Any

from src.conciliacao import conciliar_precatorios
from src.leitura import ler_arquivos
from src.pagamentos import processar_pagamentos
from src.relatorio import gravar_saidas, preparar_saidas


def executar(entrada: Path, saida: Path) -> dict[str, Any]:
    """Executa a limpeza e grava os resultados somente no diretório de saída."""
    fontes = ler_arquivos(entrada)
    precatorios, problemas_precatorios = conciliar_precatorios(
        fontes["tribunal"], fontes["hub"], fontes["apresentacoes"]
    )
    pagamentos, ocorrencias = processar_pagamentos(fontes["pagamentos"], precatorios)
    ocorrencias.extend(problemas_precatorios)

    total_lidos = sum(len(registros) for registros in fontes.values())
    resultados = preparar_saidas(precatorios, pagamentos, ocorrencias, total_lidos)
    gravar_saidas(saida, resultados)
    logging.info("Limpeza concluída. Arquivos gravados em %s", saida)
    return resultados


def main() -> None:
    raiz = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Gera uma base confiável de precatórios.")
    parser.add_argument("--entrada", type=Path, default=raiz / "dados" / "entrada")
    parser.add_argument("--saida", type=Path, default=raiz / "dados" / "saida")
    argumentos = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    executar(argumentos.entrada, argumentos.saida)


if __name__ == "__main__":
    main()
