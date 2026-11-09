SELECT 'GOLD_VAZIA' AS teste, CASE WHEN COUNT(*)=0 THEN 1 ELSE 0 END AS erro
FROM dbo.vw_macro_monthly
UNION ALL
SELECT 'IPCA_INVALIDO', COUNT(*) FROM dbo.fx_macro_indicadores
WHERE indicador='IPCA' AND (valor IS NULL OR valor <= -100 OR data IS NULL)
UNION ALL
SELECT 'SELIC_INVALIDA', COUNT(*) FROM dbo.fx_macro_indicadores
WHERE indicador='SELIC' AND (valor IS NULL OR valor < 0 OR data IS NULL)
UNION ALL
SELECT 'JUROS_REAIS_NULO', COUNT(*) FROM dbo.vw_macro_real_rate
WHERE juros_reais IS NULL AND ipca_12m IS NOT NULL
UNION ALL
SELECT 'DATA_DUPLICADA', COUNT(*) FROM (
    SELECT macro_date FROM dbo.vw_macro_monthly
    GROUP BY macro_date HAVING COUNT(*) > 1
) d
UNION ALL
SELECT 'DATA_NULA', COUNT(*) FROM dbo.vw_macro_monthly WHERE macro_date IS NULL
UNION ALL
SELECT 'CAMBIO_VAZIO',
       CASE WHEN NOT EXISTS (SELECT 1 FROM silver.usd_brl)
                  OR NOT EXISTS (SELECT 1 FROM silver.eur_brl) THEN 1 ELSE 0 END
UNION ALL
SELECT 'LACUNA_IPCA', COUNT(*) FROM (
    SELECT mes, LAG(mes) OVER (ORDER BY mes) AS anterior
    FROM dbo.vw_gold_ipca
) x WHERE DATEDIFF(month, anterior, mes) <> 1
UNION ALL
SELECT 'MOEDAS_AUSENTES',
       CASE WHEN COUNT(DISTINCT currency) <> 2 THEN 1 ELSE 0 END
FROM dbo.vw_fx_monthly_summary
UNION ALL
SELECT 'IPCA_12M_INVALIDO', COUNT(*) FROM dbo.vw_macro_ipca_12m
WHERE ipca_12m IS NULL
  AND macro_date >= DATEADD(month, 11, (SELECT MIN(mes) FROM dbo.vw_gold_ipca))
UNION ALL
SELECT 'SELIC_META_INVALIDA',
       CASE
           WHEN NOT EXISTS (
               SELECT 1
               FROM dbo.fx_macro_indicadores
               WHERE indicador = 'SELIC_META'
           ) THEN 1
           ELSE 0
       END
       +
       (
           SELECT COUNT(*)
           FROM dbo.fx_macro_indicadores
           WHERE indicador = 'SELIC_META'
             AND (
                 valor IS NULL
                 OR valor < 0
                 OR data IS NULL
             )
       );
