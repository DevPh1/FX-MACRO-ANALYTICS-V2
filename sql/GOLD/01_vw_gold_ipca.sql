  -- View: vw_gold_ipca
    -- Description: View para obter os valores mensais do IPCA a partir da tabela f_macro_indicadores.
    ------------------------------------------------------------------------------------------------------------------------------------

CREATE OR ALTER VIEW dbo.vw_gold_ipca AS
SELECT
    DATEFROMPARTS(YEAR(data), MONTH(data), 1) AS mes,
    valor AS ipca
FROM dbo.fx_macro_indicadores
WHERE indicador = 'IPCA';
