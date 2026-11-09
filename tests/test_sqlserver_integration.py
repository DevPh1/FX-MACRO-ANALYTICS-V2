"""Integração opcional, somente em banco de teste vazio.
Configure FX_SQL_SERVER, FX_SQL_DATABASE e FX_INTEGRATION=1.
O teste cria objetos se ausentes; linhas e views são revertidas ao final.
"""
import os
import unittest
from math import prod
from sqlalchemy import text
from src.common import BASE_DIR, get_engine
from src.transformation.load_silver import read_inputs, load_frames
from src.transformation.sql_runner import execute_folder
from src.transformation.run_validation import validate

@unittest.skipUnless(os.environ.get('FX_INTEGRATION') == '1', 'SQL Server de teste não configurado')
class SqlServerIntegration(unittest.TestCase):
    def test_idempotency_metrics_and_rollback(self):
        db = os.environ.get('FX_SQL_DATABASE', '')
        self.assertTrue(db.endswith('_test'), 'Banco deve terminar em _test')
        frames = read_inputs(allow_legacy=True)
        engine = get_engine()
        try:
            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    conn.exec_driver_sql((BASE_DIR / 'sql/DDL/create_tables.sql').read_text())
                    for _ in range(2):
                        load_frames(conn, frames)
                    execute_folder(conn, 'GOLD')
                    execute_folder(conn, 'ANALYTICS')
                    validate(conn)
                    row = conn.exec_driver_sql('SELECT TOP (1) macro_date, ipca_12m FROM dbo.vw_macro_ipca_12m WHERE ipca_12m IS NOT NULL ORDER BY macro_date DESC').fetchone()
                    import pandas as pd
                    end = pd.Timestamp(row[0])
                    ipca = frames['IPCA']
                    selected = ipca[(ipca.data <= end) & (ipca.data > end - pd.DateOffset(months=12))]
                    expected = (prod(1 + selected.valor / 100) - 1) * 100
                    self.assertAlmostEqual(row[1], expected, places=7)
                    real = conn.exec_driver_sql('SELECT TOP (1) selic_mensal, ipca_12m, juros_reais FROM dbo.vw_macro_real_rate WHERE juros_reais IS NOT NULL ORDER BY macro_date DESC').fetchone()
                    self.assertAlmostEqual(real[2], ((1+real[0]/100)/(1+real[1]/100)-1)*100, places=3)
                    nested = conn.begin_nested()
                    conn.exec_driver_sql('DELETE FROM silver.usd_brl')
                    with self.assertRaises(RuntimeError):
                        validate(conn)
                    nested.rollback()
                    validate(conn)
                finally:
                    transaction.rollback()
        finally:
            engine.dispose()
