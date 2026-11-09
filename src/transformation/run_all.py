"""Refresh opcional e publicação transacional das transformações."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.common import get_engine
from src.transformation.load_silver import read_inputs, load_frames
from src.transformation.sql_runner import execute_folder
from src.transformation.run_validation import validate

def run_all(refresh=False, allow_legacy=False):
    if refresh:
        from src.ingestion.bcb_api import run_ingestion
        run_ingestion()
    frames = read_inputs(allow_legacy)
    engine = get_engine()
    try:
        with engine.begin() as conn:
            load_frames(conn, frames)
            execute_folder(conn, 'GOLD')
            execute_folder(conn, 'ANALYTICS')
            validate(conn)
        print('Transformações validadas e confirmadas na mesma transação.')
    finally:
        engine.dispose()

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--refresh', action='store_true', help='Coletar a API antes da carga')
    p.add_argument('--legacy-snapshot', action='store_true', help='Aceitar CSVs antigos sem manifest; não atualiza a API')
    args = p.parse_args()
    run_all(args.refresh, args.legacy_snapshot)
