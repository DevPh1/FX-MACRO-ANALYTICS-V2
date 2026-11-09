
-- View GOLD: Meta SELIC definida pelo Copom
-- Fonte: Banco Central do Brasil, SGS 432

CREATE OR ALTER VIEW dbo.vw_gold_selic_meta AS
SELECT
    CAST(data AS DATE) AS data,
    CAST(valor AS FLOAT) AS selic_meta_aa
FROM dbo.fx_macro_indicadores
WHERE indicador = 'SELIC_META';
