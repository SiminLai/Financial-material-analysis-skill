import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers.document_pipeline import parse_document
from runtime.runtime import source_hash, write_json


def evaluate(document, labels):
    checks = []
    for label in labels:
        expected = label['row']
        candidates = [table for table in document['table_regions'] if table.get('page') == label['page']]
        checks.append({'page': label['page'], 'expected_row': expected,
                       'exact_row_match': any([str(cell if cell is not None else '').strip() for cell in row] == expected
                                              for table in candidates for row in table['rows']),
                       'located_table': any(table.get('bbox') for table in candidates)})
    return {'checks': checks, 'labeled_rows': len(checks),
            'exact_row_accuracy': sum(check['exact_row_match'] for check in checks) / len(checks) if checks else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('--output', default='workspace/benchmark/report.json')
    parser.add_argument('--engines', nargs='+', choices=['native', 'docling'], default=['native', 'docling'])
    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    runs = []
    for case in manifest['cases']:
        path = (manifest_path.parent / case['file']).resolve()
        for engine in args.engines:
            started = time.monotonic()
            record = {'case': case['id'], 'engine': engine, 'labels_reviewed': case.get('reviewed', False)}
            try:
                if not case.get('reviewed') or not case.get('rows'):
                    raise ValueError('Human-reviewed row labels required')
                checksum = source_hash(path)
                if checksum != case.get('sha256'):
                    raise ValueError('Source SHA256 missing or mismatched')
                document = parse_document(path, engine=engine)
                record.update(evaluate(document, case['rows']))
                record.update(status='completed', source_sha256=checksum, metadata=document['meta'])
            except Exception as error:
                record.update(status='failed', error=type(error).__name__ + ': ' + str(error))
            record['seconds'] = round(time.monotonic() - started, 3)
            runs.append(record)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, {'runs': runs, 'default_engine_changed': False,
                        'limitations': 'Exact labeled row matching only; not a financial accuracy or investment benchmark'})
    return 0 if runs and all(run['status'] == 'completed' for run in runs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
