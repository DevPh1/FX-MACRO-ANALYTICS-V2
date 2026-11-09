from pathlib import Path
from src.common import BASE_DIR, get_engine

def execute_folder(conn, folder):
    files = sorted((BASE_DIR / 'sql' / folder).glob('*.sql'))
    if not files:
        raise FileNotFoundError(f'Sem SQL em {folder}')
    for path in files:
        print(f'Executando {folder}/{path.name}')
        conn.exec_driver_sql(path.read_text(encoding='utf-8'))

def run_folder(folder, conn=None):
    if conn is not None:
        execute_folder(conn, folder)
        return
    engine = get_engine()
    try:
        with engine.begin() as active:
            execute_folder(active, folder)
    finally:
        engine.dispose()
