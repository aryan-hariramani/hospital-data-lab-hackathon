"""Record measured performance and controlled-defect results, without thresholds."""
import json
import platform
import sqlite3
import statistics
from pathlib import Path
from time import perf_counter
from hospital_data.core import generate_visits, inject_demo_errors
from hospital_data.validation import validate
from hospital_data.database import connect, replace_visits, analytics

def benchmark():
    samples = []
    for _ in range(5):
        start = perf_counter()
        rows = generate_visits(10000, 42)
        generated = perf_counter()
        clean, report = validate(rows)
        validated = perf_counter()
        conn = connect()
        try:
            replace_visits(conn, clean)
            summary = analytics(conn)['summary']
        finally: conn.close()
        end = perf_counter()
        assert len(clean) == 10000 and sum(d['visits'] for d in summary) == 10000
        samples.append({'generation_seconds': generated-start, 'validation_seconds': validated-generated,
                        'sqlite_load_and_query_seconds': end-validated, 'total_seconds': end-start})
    corrupted, expected = inject_demo_errors(rows)
    accepted, report = validate(corrupted)
    detected = set(report['invalid_indices'])
    result = {
        'python': platform.python_version(), 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version,
        'visits': 10000, 'departments': 5, 'seed': 42, 'repetitions': len(samples),
        'median_seconds': {key: round(statistics.median(s[key] for s in samples), 6) for key in samples[0]},
        'samples_seconds': samples,
        'controlled_defects': {'injected_rows': len(expected), 'categories': len(set(expected.values())),
            'detected_injected_rows': len(set(expected) & detected), 'missed_injected_rows': len(set(expected)-detected),
            'additional_flagged_rows': len(detected-set(expected)), 'accepted_rows': len(accepted)},
        'scope': 'Local timing includes a second validation during SQLite loading; excludes disk and CSV export. '
                 'Defect results apply only to the deliberately corrupted fixture, not arbitrary input.'}
    target = Path('reports/benchmark.json')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__': benchmark()
