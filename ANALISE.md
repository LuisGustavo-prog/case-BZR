# Análise do case: precatórios

Este documento reúne o diagnóstico, as propostas de prevenção e as dúvidas, na ordem pedida no enunciado.

## Diagnóstico

---

### 1. O total pago é calculado errado

Pelo passo 2 do fluxo, o script soma cada valor ao total do processo, sem olhar o tipo e sem tratar repetição. Isso gera dois erros.

**Repetição e correção de eventos**

* `pagamentos.json`, registros 2 e 4: `ev-002` aparece duas vezes, idêntico (2.500,50).
* `pagamentos.json`, registros 1 e 9: `ev-001` aparece com 15.000,00 e depois com 15.500,00 (`atualizado_em` mais novo), o que parece uma correção.
* O arquivo vem todo dia com os últimos 7 dias, e o operador reroda o script quando falha. O mesmo evento pode, portanto, entrar várias vezes.
* `schema.sql`: `pagamento` não tem `UNIQUE` em `evento_id`.

Exemplo, processo `0012345-10.2019.8.26.0053`: o correto é 15.500,00 + 2.500,50 = **18.000,50**. Somando todos os registros, daria **35.501,00**.

**Estorno somado como pagamento**

* `pagamentos.json`, registros 7 e 8 (processo `0034567-32.2018.8.26.0405`): `ev-006` é pagamento de 5.000 e `ev-007` é **estorno** de 5.000.
* O correto é 0,00 pago. Somando tudo, daria **10.000,00**.

**Impacto**: o sistema mostra como pago um valor que o tribunal não considera pago, e é o principal candidato a explicar "os números não batem".

**Causa ou consequência**: causa. O erro do estorno nasce da documentação, que diz que `tipo` é sempre "pagamento" (item 5).

---

### 2. Eventos inválidos somem em silêncio

Pelo passo 5, o script ignora o que não consegue importar e ninguém é avisado.

| Registro | Evento | Problema |
|---|---|---|
| 5 | `ev-004` | `valor` nulo (processo `0023456-21.2020.8.26.0053`) |
| 6 | `ev-005` | processo sem pontuação, `00234562120208260053`, valor 1.200,00 |
| 11 | `ev-009` | `valor` negativo (-200) |
| 12 | `ev-010` | `processo` vazio, valor 750,00 |
| 13 | `ev-011` | processo `0067890-65.2016.8.26.0053`, que não existe no `hub.csv`, valor 4.000,00 |

**Impacto**: pelo menos **R$ 5.950,00** em valores positivos (`ev-005`, `ev-010`, `ev-011`) podem sumir do total, e a operação não tem como saber que a diferença existe. Parte é recuperável: `ev-005` é claramente o processo `0023456-21.2020.8.26.0053` sem pontuação.

**Causa ou consequência**: consequência dos itens 4 e 5, mas é o que **esconde** todos os outros problemas.

---

### 3. O prazo de pagamento sai errado

Regra do enunciado, como li: apresentado **até** 2 de abril (inclusive) vence em 31/12 do ano seguinte. Depois disso, vence em 31/12 do ano subsequente ao seguinte. Para datas com horário, usei a data local do Brasil (UTC-3).

| Processo | `apresentado_em` | Prazo no hub | Prazo correto |
|---|---|---|---|
| `0012345-10.2019.8.26.0053` | 2025-04-02 (registro 1) | 2027-12-31 (linha 2) | **2026-12-31** |
| `0023456-21.2020.8.26.0053` | 2025-04-03 | 2027-12-31 | ok |
| `0034567-32.2018.8.26.0405` | 2024-02-29 (bissexto) | 2025-12-31 | ok |
| `0045678-43.2021.5.02.0011` | 2025-04-02T23:30:00-03:00 | 2026-12-31 | ok |
| `0056789-54.2017.4.03.6100` | 2025-04-03T01:00:00Z (registro 5), que é 02/04 22:00 em Brasília | 2027-12-31 (linha 6) | **2026-12-31** (confirmar fuso) |
| `0067890-65.2016.8.26.0053` | 2023-12-31 | não está no hub | 2025-12-31 |

**Impacto**: dois precatórios (face somada de **R$ 67.000,00**) aparecem com prazo um ano depois do real. A equipe prioriza a carteira por esse prazo, então eles ficam atrás de precatórios menos urgentes.

**Hipótese**: o sistema usa só os 10 primeiros caracteres da data. Isso explicaria os dois erros (dia 2 tratado como fora do prazo e `...T01:00:00Z` lido como dia 3).

**Causa ou consequência**: causa de priorização errada. Consequência dos formatos de data misturados (item 5).

---

### 4. A conciliação manual não pega as divergências

Pelo passo 3, o operador abre o `tribunal.csv` no Excel, salva e compara com o `hub.csv` procurando nome e número "exatamente como estão escritos".

**Divergências reais que esse método deixa passar**

| Divergência | Onde |
|---|---|
| Valor de face: 31.000,00 no hub e 30.000,00 no tribunal | `hub.csv` linha 3, `tribunal.csv` linha 3 (`0023456`) |
| Ente devedor: "Município de Santos" no hub e "União" no tribunal | `hub.csv` linha 5, `tribunal.csv` linha 5 (`0045678`) |
| Processo só no hub | `0056789-54.2017.4.03.6100`, `hub.csv` linha 6 |
| Processo só no tribunal | `0067890-65.2016.8.26.0053`, `tribunal.csv` linha 6 |

**A cadeia que mostra como um problema vira outro (exemplo do processo `0023456`)**

1. O número do processo não tem padrão: no `hub.csv` linha 3 e em `pagamentos.json` registro 6 ele aparece como `00234562120208260053` (20 dígitos), enquanto os demais usam o formato CNJ de 25 caracteres.
2. O `schema.sql` define `numero_processo CHAR(20)`, que não comporta o formato CNJ documentado. Ou seja, o banco e a documentação já discordam sobre o formato.
3. Por causa disso, a busca por texto exato falha: o evento `ev-005` não acha seu precatório (item 2) e o operador não acha a linha equivalente no outro arquivo.
4. Quando o operador não acha, não consegue comparar, e a divergência de 1.000 no valor de face passa sem ser vista.

O mesmo vale para o nome do ente: `MUNICIPIO DE SAO PAULO` (hub linha 2) e `Município de São Paulo` (tribunal linha 2) são o mesmo ente, mas a busca exata não os iguala.

**Impacto**: das 6 situações de processo, 4 têm divergência real de valor, de ente ou de existência. Abrir e salvar no Excel também pode regravar a codificação e a formatação do arquivo original.

**Causa ou consequência**: consequência do número sem padrão e dos formatos misturados (item 5). Por sua vez, é causa de os problemas dos itens 1 a 3 não serem percebidos.

---

### 5. Não existe um contrato de dados que funcione na prática

Este é o problema de fundo. Os arquivos não seguem a documentação, e o schema não segue nem os arquivos.

**Documentação (`DOCUMENTACAO_TRIBUNAL.md`, v2.1) contra a realidade**

| A documentação diz | O arquivo real tem |
|---|---|
| `tribunal.csv` em UTF-8 | ISO-8859-1 (Latin-1) |
| campos separados por vírgula | separados por ponto e vírgula |
| `valor_face` com ponto decimal | `45.000,00` |
| `tipo` é sempre "pagamento" | existe "estorno" (`ev-007`) |
| `valor` é número | texto (`"2.500,50"`, registro 2), nulo (registro 5), negativo (registro 11) |
| `data_pagamento` em AAAA-MM-DD | `"10/04/2025"` (registro 2) |
| `evento_id` é único | `ev-001` e `ev-002` repetidos |
| (não documentado) | `apresentacoes.json`, com `apresentado_em` em 3 formatos (registros 4 e 5) |

**Schema (`schema.sql`)**

* Sem `UNIQUE` em `evento_id`.
* `CHAR(20)` não comporta o CNJ formatado.
* Sem `apresentado_em` nem `prazo_pagamento`, que o `hub.csv` exporta, então o schema está desatualizado.
* `ente_devedor` é texto livre, o que permite variações de escrita.

**Impacto**: quem escreve o script confia no contrato e escreve regras erradas (por exemplo, assume que todo evento é um pagamento). Valores como `"2.500,50"` e datas como `10/04/2025` (que também podem ser lidas como 4 de outubro) quebram qualquer leitura ingênua.

**Causa ou consequência**: causa dos itens 1 a 4.

---

### Pontos menores (ver T4, T11 e T12 em Dúvidas)

* `ev-001` tem `data_pagamento` 2025-03-10, **antes** da apresentação do precatório (2025-04-02). E o arquivo deveria cobrir 7 dias, mas as datas de pagamento vão de 2025-02-20 a 2025-08-10.
* O precatório `0056789-54.2017.4.03.6100` tem número de Justiça Federal (J=4, TRF3) mas ente "Estado de São Paulo" no hub, o que é incomum (hipótese, não confirmada).
* Os dígitos verificadores do CNJ não conferem em nenhum dos 6 processos. Como o enunciado diz que os dados são fictícios, não tratei isso como problema.

---

## Prevenção

Cada proposta responde a um dos 5 problemas do diagnóstico. A tabela mostra o que muda em cada camada, e as seções seguintes detalham.

| Problema | No processo | No script | No banco |
|---|---|---|---|
| 1. Total pago errado | Reimportar o mesmo arquivo passa a ser seguro | Atualiza por `evento_id` e `atualizado_em`. Estorno subtrai | `UNIQUE` em `evento_id`, coluna `atualizado_em`, total calculado por view |
| 2. Eventos somem em silêncio | Alguém responde pela fila de rejeitados | Rejeita com motivo e resume cada importação | Tabelas `importacao` e `pagamento_rejeitado` |
| 3. Prazo errado | Uma única regra de prazo, escrita uma vez | Função de prazo com testes | `apresentado_em` e `prazo_pagamento` calculado |
| 4. Conciliação não pega divergências | Comparação automática, sem Excel | Normaliza processo e nome do ente | `numero_processo` canônico, com `CHECK` |
| 5. Sem contrato de dados | Leiaute versionado e validado com o tribunal | Recusa arquivo fora do contrato | Restrições que impedem dado inválido |

### No processo

* **Guardar o arquivo original sem tocar nele.** O arquivo recebido é guardado como veio. O Excel deixa de fazer parte do fluxo, e com isso some o risco de regravar codificação e formatação.
* **Conciliação automática.** Um script compara o `tribunal.csv` com a base e gera um relatório de divergências (valor, ente, processo só de um lado). O operador revisa o relatório em vez de procurar texto exato.
* **Dono para a fila de rejeitados.** Cada registro em quarentena tem um responsável e um prazo para ser resolvido (dúvida O4).
* **Contrato versionado com o tribunal.** Corrigir o leiaute 2.1 para refletir a realidade (ou o tribunal passar a respeitá-lo), avisar mudanças antes de aplicá-las, e recusar um arquivo inteiro com leiaute inesperado, avisando alguém.
* **Reenvio.** O que ficou em quarentena por falta de dado (valor nulo, processo vazio) pode ser pedido de volta corrigido ao tribunal.

### No script de importação

1. **Idempotente.** O mesmo arquivo importado duas vezes dá o mesmo resultado. Um evento com `evento_id` já existente só é atualizado se o `atualizado_em` for mais novo.
2. **Normaliza na entrada.** Número do processo vira 20 dígitos sem pontuação. Valores como `"2.500,50"` viram `Decimal`. Datas viram ISO. `apresentado_em` com horário vira a data local do Brasil (UTC-3).
3. **Respeita o tipo.** Estorno subtrai. O total pago não é acumulado a cada importação, é calculado a partir dos eventos.
4. **Nada é ignorado.** O que não pode ser importado vai para `pagamento_rejeitado` com o registro original e o motivo. No fim da importação, um resumo mostra quantos registros foram lidos, importados e rejeitados.
5. **Uma transação por arquivo.** Se a importação falhar no meio, nada fica pela metade, e rodar de novo é seguro por causa do item 1.
6. **Testes** para as regras de maior risco: prazo (dia 2 de abril, fuso, ano bissexto), correção de evento por `atualizado_em`, estorno e normalização do número do processo.

O comando que implementa o item 1 (testado no PostgreSQL). Os `%s` são os espaços onde o Python coloca os valores de cada evento:

```sql
INSERT INTO pagamento (precatorio_id, evento_id, tipo, valor, pago_em, atualizado_em)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (evento_id) DO UPDATE
SET precatorio_id = EXCLUDED.precatorio_id,
    tipo          = EXCLUDED.tipo,
    valor         = EXCLUDED.valor,
    pago_em       = EXCLUDED.pago_em,
    atualizado_em = EXCLUDED.atualizado_em
WHERE pagamento.atualizado_em < EXCLUDED.atualizado_em;
```

Resultado com o evento `ev-001`:

| Situação | Resultado |
|---|---|
| Chega pela primeira vez (15.000, de 10/03) | Insere |
| O mesmo arquivo é importado de novo | Não faz nada, porque é a mesma versão |
| Chega a correção (15.500, de 11/03) | Atualiza para 15.500 |
| A versão antiga chega depois da nova | Não faz nada, porque é mais velha |

### No banco

O SQL abaixo está também em `prevencao.sql`. Ele deve rodar **depois** do recálculo do zero (dúvida O2), porque o `UNIQUE` em `evento_id` falha se ainda houver eventos duplicados.

```sql
-- Migração de prevenção. Rodar DEPOIS do recálculo do zero (dúvida O2),
-- porque o UNIQUE em evento_id falha se ainda existirem duplicados.

BEGIN;

-- 1. Identificador canônico: 20 dígitos, sem pontuação.
--    A formatação CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) fica só na exibição.
ALTER TABLE precatorio
    ADD CONSTRAINT ck_precatorio_numero_canonico
    CHECK (numero_processo ~ '^[0-9]{20}$');

-- 2. Evento único e versionado: o mesmo evento_id nunca vira duas linhas,
--    e a versão mais nova (atualizado_em) substitui a antiga.
ALTER TABLE pagamento ADD COLUMN atualizado_em TIMESTAMPTZ;
UPDATE pagamento SET atualizado_em = criado_em WHERE atualizado_em IS NULL;
ALTER TABLE pagamento ALTER COLUMN atualizado_em SET NOT NULL;
ALTER TABLE pagamento
    ADD CONSTRAINT uq_pagamento_evento UNIQUE (evento_id);

-- 3. Cada arquivo recebido fica registrado, com contadores.
CREATE TABLE importacao (
    id                BIGSERIAL PRIMARY KEY,
    arquivo_nome      TEXT        NOT NULL,
    recebido_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_lidos       INTEGER     NOT NULL DEFAULT 0,
    total_importados  INTEGER     NOT NULL DEFAULT 0,
    total_rejeitados  INTEGER     NOT NULL DEFAULT 0
);

-- 4. Nada é ignorado em silêncio: o que não entra vai para quarentena,
--    com o registro original e o motivo.
CREATE TABLE pagamento_rejeitado (
    id             BIGSERIAL PRIMARY KEY,
    importacao_id  BIGINT      NOT NULL REFERENCES importacao (id),
    registro       INTEGER     NOT NULL,             -- posição no arquivo, a partir de 1
    evento_id      TEXT,
    payload        JSONB       NOT NULL,             -- registro exatamente como veio
    motivo         TEXT        NOT NULL,
    status         TEXT        NOT NULL DEFAULT 'aberto'
                   CHECK (status IN ('aberto', 'resolvido', 'descartado')),
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (importacao_id, registro)
);

-- 5. Data de apresentação (data local do Brasil) e prazo calculado em um só lugar.
--    Até 2 de abril (inclusive): 31/12 do ano seguinte. Depois: 31/12 do ano subsequente.
ALTER TABLE precatorio ADD COLUMN apresentado_em DATE;
ALTER TABLE precatorio
    ADD COLUMN prazo_pagamento DATE GENERATED ALWAYS AS (
        make_date(
            EXTRACT(YEAR FROM apresentado_em)::int
            + CASE WHEN apresentado_em
                        <= make_date(EXTRACT(YEAR FROM apresentado_em)::int, 4, 2)
                   THEN 1 ELSE 2 END,
            12, 31)
    ) STORED;

-- 6. Total pago derivado, nunca acumulado: estorno subtrai, e o total
--    pode ser recalculado a qualquer momento a partir dos eventos.
CREATE VIEW precatorio_total_pago AS
SELECT p.id AS precatorio_id,
       p.numero_processo,
       p.valor_face,
       COALESCE(SUM(CASE pg.tipo
                        WHEN 'pagamento' THEN  pg.valor
                        WHEN 'estorno'   THEN -pg.valor
                    END), 0) AS total_pago
FROM precatorio p
LEFT JOIN pagamento pg ON pg.precatorio_id = p.id
GROUP BY p.id;

COMMIT;
```

Decisões por trás do SQL:

* **Número do processo em 20 dígitos.** O `CHAR(20)` do schema atual já comportava essa forma. O problema estava em entrar também a forma formatada, então a regra passa a ser guardar só os 20 dígitos e formatar na exibição.
* **Prazo como coluna calculada.** A regra do prazo fica em um só lugar do banco. A limpeza em Python tem a própria função, e os testes usam os 6 processos do case para garantir que as duas dão o mesmo resultado.
* **Total pago como view.** Não existe coluna de total que possa sair de sincronia com os eventos.
* **Não incluí uma tabela de entes devedores.** Ela resolveria as variações de escrita do nome (`MUNICIPIO DE SAO PAULO` e `Município de São Paulo`), mas a normalização na conciliação já cobre esse caso com menos mudança. Fica como evolução possível.

---

### Perguntas ao tribunal

| # | Pergunta | Evidência | Tratamento provisório | Bloqueia? |
|---|---|---|---|---|
| T1 | O `tribunal.csv` é a fonte oficial de ente devedor e valor de face quando divergir do nosso sistema? | Itens 4 e 5 do diagnóstico | Sim. Vale o tribunal, e a diferença vai para o relatório | Sim |
| T2 | O valor de face do processo `0023456-21.2020.8.26.0053` é 30.000,00 ou 31.000,00? Houve atualização de valor? | `tribunal.csv` linha 3 (30.000,00), `hub.csv` linha 3 (31000.00) | Usa 30.000,00 e marca como **corrigido** | Sim |
| T3 | O ente devedor do processo `0045678-43.2021.5.02.0011` é a União ou o Município de Santos? | `tribunal.csv` linha 5 (União), `hub.csv` linha 5 (Município de Santos) | Precatório e pagamentos dele ficam fora da base confiável e vão para o relatório como **em dúvida**, porque são entes diferentes e não um erro de escrita | Sim |
| T4 | O processo `0056789-54.2017.4.03.6100` não consta na lista. Foi pago, baixado ou a lista veio incompleta? Também: o ente é mesmo o Estado de São Paulo, sendo um número de Justiça Federal? | `hub.csv` linha 6, ausente do `tribunal.csv`. Número com J=4 e TR=03 | Sai da base confiável e vai para o relatório como **em dúvida** | Sim |
| T5 | O processo `0067890-65.2016.8.26.0053` é um precatório novo que ainda não chegou ao nosso sistema? | `tribunal.csv` linha 6, ausente do `hub.csv`. Tem o evento `ev-011` (4.000,00) e apresentação em `apresentacoes.json` registro 6 | Inclui na base e importa o `ev-011`. Marca como **corrigido** (criado a partir do tribunal) | Não |
| T6 | "Até 2 de abril" inclui o dia 2? E para datas com horário, vale o horário de Brasília (UTC-3)? | `0012345` apresentado em 2025-04-02. `0056789` apresentado em 2025-04-03T01:00:00Z, que é 02/04 22:00 em Brasília | Dia 2 é inclusivo, fuso UTC-3. Os dois casos saem com prazo 2026-12-31 | Sim |
| T7 | Quando o mesmo `evento_id` vem com valor diferente, o registro de `atualizado_em` mais recente é a correção e substitui o anterior? | `ev-001` nos registros 1 (15.000,00) e 9 (15.500,00) | Vale o mais recente. Substitui, e não soma | Sim |
| T8 | Como o tribunal representa um estorno? O valor -200 é um estorno enviado de forma errada? | `ev-009` (registro 11, valor -200, tipo "pagamento"). Estorno correto em `ev-007` (registro 8) | `ev-009` vai para **em dúvida** e fora do total. `ev-007` abate o total | Sim |
| T9 | O que significam um evento sem valor e um evento sem processo? Podem ser reenviados corrigidos? | `ev-004` (registro 5, valor nulo). `ev-010` (registro 12, processo vazio, valor 750,00) | Os dois vão para **descartado** (sem dados suficientes), com motivo no relatório | Não |
| T10 | A documentação v2.1 está desatualizada? Os formatos reais (Latin-1, ponto e vírgula, `45.000,00`, estorno, `10/04/2025`) são o padrão atual? Existe versão nova? | Item 5 do diagnóstico | Lê como vierem, tolerando os formatos reais, e registra no relatório | Não |
| T11 | O `pagamentos.json` cobre só 7 dias ou o histórico? E o pagamento `ev-001` (2025-03-10) antes da apresentação do processo (2025-04-02) está com a data certa? | Datas de 2025-02-20 a 2025-08-10. `0012345` apresentado em 2025-04-02 | `ev-001` fica fora da base confiável e vai para o relatório como **em dúvida**, com o valor pendente (15.500,00) | Não |
| T12 | Os dígitos verificadores dos números de processo são válidos? | Nenhum dos 6 conferiu pelo cálculo do CNJ | Valida só o formato, não o dígito | Não |

---

### Perguntas à operação

| # | Pergunta | Evidência | Tratamento provisório | Bloqueia? |
|---|---|---|---|---|
| O1 | Podemos corrigir automaticamente números de processo sem pontuação quando os 20 dígitos casam com um único precatório? | `ev-005` (registro 6) e `hub.csv` linha 3: `00234562120208260053` | Normaliza e marca como **corrigido**. Se não casar com exatamente um precatório, vai para **em dúvida** | Sim |
| O2 | O total pago que o sistema já guarda hoje está contaminado por repetições, estornos e reimportações. Guardamos os arquivos antigos para recalcular desde o início? | Itens 1 e 2 do diagnóstico. Sem `UNIQUE` em `evento_id` | A limpeza recalcula do zero com os arquivos disponíveis. O total antigo não é aproveitado | Sim |
| O3 | Onde ficam o total pago, o `apresentado_em` e o `prazo_pagamento` no sistema real? O `schema.sql` não tem essas colunas | `schema.sql` contra as colunas do `hub.csv` | Calcula o total e o prazo a partir da base limpa, sem depender do schema atual | Sim |
| O4 | Quem decide os casos marcados como **em dúvida** e em quanto tempo? | Casos T3, T4, T8, T11 e O1 | Ficam fora da base confiável e listados no relatório, com o valor pendente, até alguém decidir | Não |
| O5 | O operador pode comparar usando o `tribunal.csv` original em vez de abrir e salvar no Excel? | Passo 3 do fluxo. O arquivo está em Latin-1 | A limpeza lê o arquivo original, sem alterá-lo | Não |

---

### Resumo do que bloqueia a produção

Sem estas respostas, a limpeza não deveria rodar em produção: **T1, T2, T3, T4, T6, T7, T8, O1, O2 e O3**.

As demais não bloqueiam, porque o tratamento provisório é seguro: o caso vai para **em dúvida** ou **descartado** com motivo registrado, e pode ser reprocessado depois.

**Regra da base confiável**: tudo que ficou **em dúvida** ou **descartado** fica fora da base confiável e vai para o relatório, com o motivo e o valor pendente. Só entram na base os casos **ok** e **corrigidos**. Se um precatório sai da base, os pagamentos dele saem junto.