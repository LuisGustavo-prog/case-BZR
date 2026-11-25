# Limpeza de precatórios

Programa em Python 3.10 ou mais recente que lê os arquivos originais em `dados/entrada/`, concilia precatórios e pagamentos e gera uma base confiável, arquivos de pendências e um relatório. Os arquivos de entrada são abertos apenas para leitura.

## Como executar

No Prompt de Comando (`cmd`), na raiz do repositório, instale a dependência usada nos testes e execute a suíte:

```cmd
python -m pip install -r requirements.txt
python -m pytest -q
```

Para gerar os arquivos em `dados/saida/`:

```cmd
python -m src.limpeza
```

Também é possível informar outros diretórios de entrada e saída:

```cmd
python -m src.limpeza --entrada "C:\caminho com espaços\entrada" --saida "C:\caminho com espaços\saida"
```

O programa gera `precatorios_limpos.csv`, `pagamentos_limpos.csv`, `fora_da_base.csv` e `relatorio.md` no diretório de saída.

## Uso de IA

Usei o ChatGPT/Codex como apoio na implementação do código de limpeza e na atualização do banco de dados. Usei o Claude para compreender melhor o projeto, analisar os dados fornecidos e elaborar o arquivo `ANALISE.md`.

### Como conferi o que a IA produziu

Revisei o código gerado e analisei a lógica que a IA aplicou em cada regra antes de aceitá-la.