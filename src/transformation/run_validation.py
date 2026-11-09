import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.common import BASE_DIR, get_engine

EXPECTED = {'GOLD_VAZIA', 'IPCA_INVALIDO', 'SELIC_INVALIDA',
            'JUROS_REAIS_NULO', 'DATA_DUPLICADA', 'DATA_NULA',
            'CAMBIO_VAZIO', 'LACUNA_IPCA', 'MOEDAS_AUSENTES',
            'IPCA_12M_INVALIDO', 'SELIC_META_INVALIDA'}

def check_results(rows):
    rows = list(rows)
    names = [str(row[0]) for row in rows]
    if len(names) != len(EXPECTED) or set(names) != EXPECTED:
        raise RuntimeError('Conjunto de testes vazio, duplicado ou incompleto')
    failures = []
    for name, count in rows:
        if count is None or int(count) != count or count < 0:
            raise ValueError(f'{name}: contagem inválida')
        print(f'Teste: {name} | Erros: {count}')
        if count > 0:
            failures.append(f'{name}={count}')
    if failures:
        raise RuntimeError('Validação reprovada: ' + ', '.join(failures))

def validate(conn):
    path = BASE_DIR / 'sql' / 'Validation' / 'validate_gold.sql'
    check_results(conn.exec_driver_sql(path.read_text(encoding='utf-8')).fetchall())

def run(conn=None):
    if conn is not None:
        validate(conn)
        return
    engine = get_engine()
    try:
        with engine.connect() as active:
            validate(active)
    finally:
        engine.dispose()

if __name__ == '__main__':
    run()
