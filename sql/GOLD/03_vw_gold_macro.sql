-- View: vw_gold_macro
    -- Description: View que combina os valores mensais do IPCA e da taxa SELIC.
    -------------------------------------------------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_gold_macro AS
SELECT
    i.mes AS ano_mes,
    i.ipca AS ipca_mensal,
    s.selic_media AS selic_mensal
FROM dbo.vw_gold_ipca i
LEFT JOIN dbo.vw_gold_selic s
    ON i.mes = s.mes
WHERE i.ipca IS NOT NULL
  AND s.selic_media IS NOT NULL;
