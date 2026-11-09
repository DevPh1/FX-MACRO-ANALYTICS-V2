
--  View to summarize monthly foreign exchange rates for USD_BRL and EUR_BRL


CREATE OR ALTER VIEW dbo.vw_fx_monthly_summary AS

SELECT
    DATEFROMPARTS(YEAR(data), MONTH(data), 1) AS fx_date,
    YEAR(data) AS [year],
    MONTH(data) AS [month],
    'USD_BRL' AS currency,
    ROUND(AVG(valor), 4) AS avg_rate,
    ROUND(MIN(valor), 4) AS min_rate,
    ROUND(MAX(valor), 4) AS max_rate
FROM silver.usd_brl
GROUP BY YEAR(data), MONTH(data)

UNION ALL

SELECT
    DATEFROMPARTS(YEAR(data), MONTH(data), 1) AS fx_date,
    YEAR(data) AS [year],
    MONTH(data) AS [month],
    'EUR_BRL' AS currency,
    ROUND(AVG(valor), 4) AS avg_rate,
    ROUND(MIN(valor), 4) AS min_rate,
    ROUND(MAX(valor), 4) AS max_rate
FROM silver.eur_brl
GROUP BY YEAR(data), MONTH(data);
