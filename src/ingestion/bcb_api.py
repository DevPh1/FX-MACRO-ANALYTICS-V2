"""Coleta todas as séries configuradas antes de publicar um snapshot."""
import json
import sys
import tempfile
import os
import hashlib
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.common import RAW_PATH, SERIES

BASE_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados'

def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2,
                  status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({'Accept': 'application/json',
                            'User-Agent': 'FX-Macro-Analytics/2'})
    return session

def process_series_data(name, info, data):
    if not isinstance(data, list) or not data:
        raise ValueError(f'{name}: resposta vazia ou formato inválido')
    df = pd.DataFrame(data)
    if not {'data', 'valor'}.issubset(df.columns):
        raise ValueError(f'{name}: campos data e valor ausentes')
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='raise')
    df['valor'] = pd.to_numeric(df['valor'].astype(str).str.replace(',', '.', regex=False), errors='raise')
    if df[['data', 'valor']].isna().any().any():
        raise ValueError(f'{name}: dado obrigatório nulo')
    if not __import__('numpy').isfinite(df['valor']).all():
        raise ValueError(f'{name}: valor não finito')
    if df['data'].duplicated().any():
        raise ValueError(f'{name}: datas duplicadas na fonte')
    df['serie'], df['codigo'], df['frequencia'] = name, info['code'], info['frequency']
    return df[['data', 'valor', 'serie', 'codigo', 'frequencia']].sort_values('data')

def fetch_bcb_series(session, code, frequency, today):
    params = {'formato': 'json'}
    if frequency == 'daily':
        params.update(dataInicial=(today - timedelta(days=3650)).strftime('%d/%m/%Y'),
                      dataFinal=today.strftime('%d/%m/%Y'))
    name = next((name for name, info in SERIES.items() if info['code'] == code), str(code))
    for attempt in range(1, 4):
        print(f'Consultando {name} (SGS {code}) | tentativa {attempt}/3', flush=True)
        response = session.get(BASE_URL.format(code), params=params, timeout=(10, 60))
        content_type = response.headers.get('Content-Type', 'não informado')
        preview = repr(response.text[:240])
        diagnostic = (f'{name} | SGS={code} | HTTP={response.status_code} | '
                      f'Content-Type={content_type} | início da resposta={preview}')
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError('API BCB retornou erro HTTP: ' + diagnostic) from exc
        try:
            if not response.content.strip():
                raise ValueError('corpo vazio')
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                raise ValueError('esperada lista não vazia de observações')
            if any(not isinstance(row, dict) or not {'data', 'valor'}.issubset(row)
                   for row in payload):
                raise ValueError('campos data/valor ausentes')
        except ValueError as exc:
            if attempt == 3:
                raise RuntimeError('API BCB sem dados JSON válidos após 3 tentativas: '
                                   + diagnostic) from exc
            print('Resposta inválida; nova tentativa. ' + diagnostic, flush=True)
            time.sleep(2 ** attempt)
            continue
        return payload

def run_ingestion():
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    # O marcador é removido antes da substituição dos CSVs: leitores rejeitam
    # um snapshot incompleto se houver falha durante a publicação.
    with make_session() as session, tempfile.TemporaryDirectory(dir=RAW_PATH.parent) as temp:
        staging = Path(temp)
        frames, summary = [], {}
        for name, info in SERIES.items():
            payload = fetch_bcb_series(session, info['code'], info['frequency'], datetime.now())
            frame = process_series_data(name, info, payload)
            (staging / f'{name}.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            target = staging / f'{name}.csv'
            frame.to_csv(target, index=False, encoding='utf-8')
            summary[name] = {'code': info['code'], 'rows': len(frame),
                'min_date': str(frame['data'].min().date()),
                'max_date': str(frame['data'].max().date()),
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
            frames.append(frame)
            print(f'{name}: {len(frame)} observações recebidas', flush=True)
        pd.concat(frames, ignore_index=True).to_csv(staging / 'bcb_consolidado.csv', index=False)
        archive = RAW_PATH / 'snapshots' / run_id
        archive.mkdir(parents=True)
        for source in staging.iterdir():
            shutil.copy2(source, archive / source.name)
        manifest = {'run_id': run_id, 'series': summary}
        (archive / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        marker = RAW_PATH / 'manifest.json'
        marker.unlink(missing_ok=True)
        for name in [*(f'{s}.csv' for s in SERIES), 'bcb_consolidado.csv']:
            os.replace(staging / name, RAW_PATH / name)
        # Publica o manifest por último. A carga verifica os hashes
        # de todos os CSVs configurados.
        shutil.copy2(archive / 'manifest.json', staging / 'manifest.json')
        os.replace(staging / 'manifest.json', marker)
    print(f'Ingestão completa: {run_id}')
    return manifest

if __name__ == '__main__':
    run_ingestion()
