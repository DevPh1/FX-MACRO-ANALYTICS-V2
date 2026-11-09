CREATE OR ALTER VIEW dbo.vw_gold_selic AS
SELECT
    DATEFROMPARTS(YEAR(data), MONTH(data), 1) AS mes,
    AVG(valor) AS selic_media
FROM dbo.fx_macro_indicadores
WHERE indicador = 'SELIC'
GROUP BY DATEFROMPARTS(YEAR(data), MONTH(data), 1);
