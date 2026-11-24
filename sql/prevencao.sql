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
