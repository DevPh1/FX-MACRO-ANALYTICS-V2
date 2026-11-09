"""Cria tabelas no banco já criado pelo usuário no SSMS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.common import BASE_DIR, get_engine

def run():
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql((BASE_DIR / 'sql' / 'DDL' / 'create_tables.sql').read_text())
    finally:
        engine.dispose()

if __name__ == '__main__':
    run()
