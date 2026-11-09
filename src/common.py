"""Configuração compartilhada sem conexão criada durante import."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = BASE_DIR / 'data' / 'RAW'
SERIES = {
    'IPCA': {'code': 433, 'frequency': 'monthly'},
    'USD_BRL': {'code': 1, 'frequency': 'daily'},
    'EUR_BRL': {'code': 21619, 'frequency': 'daily'},
    'SELIC': {'code': 1178, 'frequency': 'daily'},
    'SELIC_META': {'code': 432, 'frequency': 'daily'},
}


def get_engine(database=None):
    server = os.environ.get('FX_SQL_SERVER')
    if not server:
        raise RuntimeError('Defina FX_SQL_SERVER com a instância SQL Server.')
    driver = os.environ.get('FX_SQL_DRIVER', 'ODBC Driver 17 for SQL Server')
    db = database or os.environ.get('FX_SQL_DATABASE', 'fx_macro')
    conn_str = (f'DRIVER={{{driver}}};SERVER={server};DATABASE={db};'
                'Trusted_Connection=yes;')
    return create_engine(URL.create('mssql+pyodbc',
                         query={'odbc_connect': conn_str}),
                         fast_executemany=True)
