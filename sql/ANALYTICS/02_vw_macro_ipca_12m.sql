-- Percentual acumulado composto. A janela usa o histórico próprio do IPCA,
-- não a interseção com a série Selic. NULL para janela incompleta.
CREATE OR ALTER VIEW dbo.vw_macro_ipca_12m AS
SELECT a.mes AS macro_date, a.ipca AS ipca_mensal,
       CASE WHEN w.n = 12 AND w.validos = 12
                  AND DATEDIFF(month, w.primeiro, w.ultimo) = 11
            THEN (EXP(w.log_fatores) - 1.0) * 100.0
       END AS ipca_12m
FROM dbo.vw_gold_ipca a
CROSS APPLY (
    SELECT COUNT(*) AS n,
           COUNT(CASE WHEN b.ipca > -100 THEN 1 END) AS validos,
           MIN(b.mes) AS primeiro, MAX(b.mes) AS ultimo,
           SUM(LOG(CASE WHEN b.ipca > -100
                        THEN 1.0 + b.ipca / 100.0 END)) AS log_fatores
    FROM dbo.vw_gold_ipca b
    WHERE b.mes <= a.mes AND b.mes > DATEADD(month, -12, a.mes)
) w;
