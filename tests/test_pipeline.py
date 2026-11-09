import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.common import SERIES
from src.ingestion.bcb_api import process_series_data, run_ingestion
from src.transformation.load_silver import read_inputs
from src.transformation.run_validation import EXPECTED, check_results


class ValidationRegressionTests(unittest.TestCase):
    def test_failure_in_any_position_is_rejected(self):
        names = sorted(EXPECTED)
        for index in range(len(names)):
            with self.subTest(index=index), contextlib.redirect_stdout(io.StringIO()):
                rows = [(name, int(i == index)) for i, name in enumerate(names)]
                with self.assertRaises(RuntimeError):
                    check_results(rows)

    def test_all_pass(self):
        with contextlib.redirect_stdout(io.StringIO()):
            check_results([(name, 0) for name in EXPECTED])

    def test_empty_incomplete_duplicate_and_bad_counts(self):
        valid = [(name, 0) for name in sorted(EXPECTED)]
        for rows in [
            [],
            valid[:-1],
            valid[:-1] + [valid[0]],
            [(valid[0][0], None)] + valid[1:],
            [(valid[0][0], -1)] + valid[1:],
        ]:
            with self.subTest(rows=rows), self.assertRaises((RuntimeError, ValueError)):
                with contextlib.redirect_stdout(io.StringIO()):
                    check_results(rows)


class InputTests(unittest.TestCase):
    def test_snapshot_roundtrip_without_local_raw(self):
        """Uma coleta temporária pode ser lida sem arquivos RAW versionados."""
        payload = [{'data': '01/01/2024', 'valor': '1.2'}]
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / 'RAW'
            with (
                patch('src.ingestion.bcb_api.RAW_PATH', raw),
                patch('src.ingestion.bcb_api.fetch_bcb_series', return_value=payload),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                manifest = run_ingestion()

            self.assertEqual(set(manifest['series']), set(SERIES))
            with patch('src.transformation.load_silver.RAW_PATH', raw):
                frames = read_inputs()

            self.assertEqual(set(frames), set(SERIES))
            self.assertEqual(
                {name: len(frame) for name, frame in frames.items()},
                {name: 1 for name in SERIES},
            )
            for name, frame in frames.items():
                with self.subTest(series=name):
                    self.assertAlmostEqual(float(frame.iloc[0]['valor']), 1.2)
                    self.assertEqual(int(frame.iloc[0]['codigo']), SERIES[name]['code'])

    def test_default_rejects_untracked_snapshot(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'src.transformation.load_silver.RAW_PATH', Path(directory)
        ):
            with self.assertRaises(RuntimeError):
                read_inputs()

    def test_invalid_payloads(self):
        info = SERIES['IPCA']
        for data in [
            [],
            {},
            [{'data': '01/01/2024'}],
            [{'data': 'invalid', 'valor': '1'}],
            [{'data': '01/01/2024', 'valor': 'nan'}],
            [{'data': '01/01/2024', 'valor': 'inf'}],
            [{'data': '01/01/2024', 'valor': '1'}] * 2,
        ]:
            with self.subTest(data=data), self.assertRaises((ValueError, KeyError)):
                process_series_data('IPCA', info, data)

    def test_decimal_and_metadata(self):
        frame = process_series_data(
            'IPCA', SERIES['IPCA'], [{'data': '01/01/2024', 'valor': '0,42'}]
        )
        self.assertEqual(frame.iloc[0]['valor'], .42)
        self.assertEqual(frame.iloc[0]['codigo'], 433)

    def test_failed_collection_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / 'RAW'
            raw.mkdir()
            old = raw / 'IPCA.csv'
            old.write_text('snapshot anterior')
            with (
                patch('src.ingestion.bcb_api.RAW_PATH', raw),
                patch(
                    'src.ingestion.bcb_api.fetch_bcb_series',
                    side_effect=RuntimeError('HTTP failure'),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    run_ingestion()
            self.assertEqual(old.read_text(), 'snapshot anterior')
            self.assertFalse((raw / 'manifest.json').exists())

    def test_success_manifest_and_tamper_detection(self):
        payload = [{'data': '01/01/2024', 'valor': '1.2'}]
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / 'RAW'
            with (
                patch('src.ingestion.bcb_api.RAW_PATH', raw),
                patch('src.ingestion.bcb_api.fetch_bcb_series', return_value=payload),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                manifest = run_ingestion()
            self.assertEqual(set(manifest['series']), set(SERIES))
            self.assertTrue(list((raw / 'snapshots').glob('*/IPCA.json')))
            with patch('src.transformation.load_silver.RAW_PATH', raw):
                frames = read_inputs()
                self.assertEqual(set(frames), set(SERIES))
                with (raw / 'IPCA.csv').open('a') as out:
                    out.write('\n')
                with self.assertRaisesRegex(ValueError, 'hash'):
                    read_inputs()


if __name__ == '__main__':
    unittest.main()
