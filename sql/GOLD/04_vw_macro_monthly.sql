--////////////////////////////////////////////////////////////////////////////////////////////////////
-- View: vw_macro_monthly
-- Description:
-- Consolida indicadores macroeconômicos em base mensal (IPCA e SELIC),
-- servindo como camada GOLD para análises econômicas.
--////////////////////////////////////////////////////////////////////////////////////////////////////
CREATE OR ALTER VIEW dbo.vw_macro_monthly AS
SELECT
    ipca_mensal,
    selic_mensal,
    CONVERT(date, ano_mes) AS macro_date
FROM dbo.vw_gold_macro;
