"""Valida entradas e substitui as quatro séries na mesma transação."""
import sys
import json
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import text
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.common import RAW_PATH, SERIES, get_engine

def read_inputs(allow_legacy=False):
    marker = RAW_PATH / 'manifest.json'
    if not marker.exists() and not allow_legacy:
        raise RuntimeError('Snapshot sem manifest. Execute ingestão ou use --legacy-snapshot para os CSVs antigos.')
    manifest = json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else None
    frames = {}
    for name, info in SERIES.items():
        file = RAW_PATH / f'{name}.csv'
        # Lê bytes uma vez, para validar e interpretar exatamente o mesmo conteúdo.
        import io
        payload = file.read_bytes()
        if manifest and hashlib.sha256(payload).hexdigest() != manifest['series'][name]['sha256']:
            raise ValueError(f'{name}: hash diferente do manifest')
        df = pd.read_csv(io.BytesIO(payload))
        required = {'data', 'valor', 'serie', 'codigo', 'frequencia'}
        if df.empty or not required.issubset(df.columns):
            raise ValueError(f'{name}: entrada vazia ou contrato incompleto')
        if not df['serie'].eq(name).all() or not df['codigo'].eq(info['code']).all() or not df['frequencia'].eq(info['frequency']).all():
            raise ValueError(f'{name}: metadados de série divergentes')
        df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d', errors='raise')
        df['valor'] = pd.to_numeric(df['valor'], errors='raise')
        if df[['data', 'valor']].isna().any().any() or not np.isfinite(df['valor']).all():
            raise ValueError(f'{name}: valores nulos ou não finitos')
        if not df['data'].eq(df['data'].dt.normalize()).all() or df['data'].duplicated().any():
            raise ValueError(f'{name}: data não diária ou duplicada')
        if name == 'IPCA' and (not df['data'].dt.day.eq(1).all() or df['valor'].le(-100).any()):
            raise ValueError('IPCA: referência mensal ou taxa inválida')
        if name in ('USD_BRL', 'EUR_BRL') and df['valor'].le(0).any():
            raise ValueError(f'{name}: cotação não positiva')
        frames[name] = df
    return frames


def load_frames(conn, frames):
    indicadores = ('IPCA', 'SELIC', 'SELIC_META')

    # Carrega os indicadores macroeconômicos.
    for name in indicadores:
        final = frames[name][['data', 'valor']].copy()

        final['indicador'] = name
        final['frequencia'] = SERIES[name]['frequency']
        final['fonte'] = 'BCB'

        conn.execute(
            text(
                'DELETE FROM dbo.fx_macro_indicadores '
                'WHERE indicador = :name'
            ),
            {'name': name}
        )

        final.to_sql(
            'fx_macro_indicadores',
            conn,
            schema='dbo',
            if_exists='append',
            index=False,
            chunksize=100,
            method='multi'
        )

    # Carrega as séries cambiais.
    for name, table in [
        ('USD_BRL', 'usd_brl'),
        ('EUR_BRL', 'eur_brl')
    ]:
        conn.execute(
            text(f'DELETE FROM silver.{table}')
        )

        frames[name][['data', 'valor']].to_sql(
            table,
            conn,
            schema='silver',
            if_exists='append',
            index=False,
            chunksize=100,
            method='multi'
        )

    # Confere a quantidade de registros persistidos.
    for name, frame in frames.items():
        if name in indicadores:
            count = conn.execute(
                text(
                    'SELECT COUNT(*) '
                    'FROM dbo.fx_macro_indicadores '
                    'WHERE indicador = :name'
                ),
                {'name': name}
            ).scalar_one()
        else:
            table = {
                'USD_BRL': 'usd_brl',
                'EUR_BRL': 'eur_brl'
            }[name]

            count = conn.exec_driver_sql(
                f'SELECT COUNT(*) FROM silver.{table}'
            ).scalar_one()

        if count != len(frame):
            raise RuntimeError(
                f'{name}: contagem persistida divergente'
            )

        print(
            f'{name}: {count} registros conferidos no banco'
        )


def run(conn=None, allow_legacy=False):
    frames = read_inputs(allow_legacy)
    if conn is not None:
        load_frames(conn, frames)
    else:
        engine = get_engine()
        try:
            with engine.begin() as active:
                load_frames(active, frames)
        finally:
            engine.dispose()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--legacy-snapshot', action='store_true')
    run(allow_legacy=parser.parse_args().legacy_snapshot)
