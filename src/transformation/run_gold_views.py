import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.transformation.sql_runner import run_folder

def run(conn=None):
    run_folder('GOLD', conn)

if __name__ == '__main__':
    run()
