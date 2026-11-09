-- Indicador ex post de cenário: média mensal da Selic em % a.a. dividida
-- pelo fator do IPCA observado em 12 meses. Não é retorno de investimento.
CREATE OR ALTER VIEW dbo.vw_macro_real_rate AS
SELECT m.macro_date, m.selic_mensal, i.ipca_12m,
       CASE WHEN i.ipca_12m > -100
            THEN ROUND(((1.0 + m.selic_mensal / 100.0) /
                        (1.0 + i.ipca_12m / 100.0) - 1.0) * 100.0, 4)
       END AS juros_reais
FROM dbo.vw_macro_monthly m
JOIN dbo.vw_macro_ipca_12m i ON m.macro_date = i.macro_date;
