# Limpeza de precatórios

Programa em Python 3.10 ou mais recente que lê os arquivos originais em `dados/entrada/`, concilia precatórios e pagamentos e gera uma base confiável, arquivos de pendências e um relatório. Os arquivos de entrada são abertos apenas para leitura.

## Como executar

Na raiz do repositório, instale a dependência usada nos testes e execute a suíte:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

Para gerar os arquivos em `dados/saida/`:

```powershell
python -m src.limpeza
```

Também é possível informar outros diretórios de entrada e saída:

```powershell
python -m src.limpeza --entrada caminho/para/entrada --saida caminho/para/saida
```

O programa gera `precatorios_limpos.csv`, `pagamentos_limpos.csv`, `fora_da_base.csv` e `relatorio.md` no diretório de saída.

## Uso de IA

Usei ChatGPT/Codex como apoio para entender o enunciado, organizar a implementação em módulos, revisar decisões e escrever partes do código e dos testes. Conferi as regras contra o enunciado e os dados fornecidos, comparei os totais e situações gerados com os resultados esperados do case e revisei os arquivos de saída. A suíte pytest foi executada e passou.
