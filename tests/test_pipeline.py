import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from hospital_data.core import generate_visits, inject_demo_errors, csv_text, FIELDS, DEPARTMENTS
from hospital_data.validation import validate
from hospital_data.database import connect, replace_visits, analytics

class GeneratorTests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(generate_visits(200, 42), generate_visits(200, 42))
    def test_different_seeds(self):
        self.assertNotEqual(generate_visits(10, 1), generate_visits(10, 2))
    def test_unique_identifiers(self):
        self.assertEqual(len({r['visit_id'] for r in generate_visits(10000)}), 10000)
    def test_all_departments(self):
        self.assertEqual({r['department'] for r in generate_visits(1000)}, set(DEPARTMENTS))
    def test_count_limits(self):
        for count in [0, -1, 100001, True, 3.5]:
            with self.subTest(count=count), self.assertRaises(ValueError): generate_visits(count)
    def test_seed_type(self):
        with self.assertRaises(ValueError): generate_visits(10, 'x')
    def test_generated_pass(self):
        clean, report = validate(generate_visits(1000))
        self.assertEqual(len(clean), 1000)
        self.assertEqual(report['invalid_rows'], 0)
    def test_csv_round_trip(self):
        rows = generate_visits(20)
        clean, report = validate(list(csv.DictReader(io.StringIO(csv_text(rows)))))
        self.assertEqual(report['invalid_rows'], 0)
        self.assertEqual(rows, clean)
    def test_no_extra_identifiers(self):
        self.assertEqual(set(generate_visits(1)[0]), set(FIELDS))

class ValidatorTests(unittest.TestCase):
    def setUp(self): self.row = generate_visits(1)[0]
    def assert_rule(self, changes, rule):
        self.row.update(changes)
        clean, report = validate([self.row])
        self.assertEqual(clean, [])
        self.assertIn(rule, report['rule_counts'])
    def test_missing(self): self.assert_rule({'department': ''}, 'schema')
    def test_extra_column(self): self.assert_rule({'extra': 'x'}, 'schema')
    def test_id(self): self.assert_rule({'visit_id': 'x'}, 'identifier')
    def test_duplicate(self):
        clean, report = validate([self.row, dict(self.row)])
        self.assertEqual(len(clean), 1)
        self.assertEqual(report['invalid_indices'], [1])
    def test_department(self): self.assert_rule({'department': 'unknown'}, 'department')
    def test_age(self): self.assert_rule({'age': 121}, 'age')
    def test_float(self): self.assert_rule({'age': 23.5}, 'age')
    def test_boolean(self): self.assert_rule({'age': True}, 'age')
    def test_impossible_date(self): self.assert_rule({'arrival_at': '2025-02-30T12:00'}, 'timestamp')
    def test_timezone(self): self.assert_rule({'arrival_at': '2025-01-01T12:00+01:00'}, 'timestamp')
    def test_chronology(self): self.assert_rule({'discharged_at': '2024-01-01T00:00'}, 'chronology')
    def test_wait(self): self.assert_rule({'wait_minutes': -1}, 'wait')
    def test_stay(self): self.assert_rule({'stay_minutes': -1}, 'stay')
    def test_duration(self): self.assert_rule({'wait_minutes': self.row['wait_minutes']+1}, 'duration')
    def test_empty(self): self.assertEqual(validate([])[1]['invalid_rows'], 0)
    def test_nulls(self): self.assert_rule({'age': None, 'arrival_at': None}, 'schema')
    def test_nan(self): self.assert_rule({'wait_minutes': float('nan')}, 'wait')
    def test_no_mutation(self):
        before = dict(self.row)
        validate([self.row])
        self.assertEqual(self.row, before)
    def test_controlled_defects(self):
        rows = generate_visits(10000)
        corrupted, expected = inject_demo_errors(rows)
        clean, report = validate(corrupted)
        self.assertEqual(set(report['invalid_indices']), set(expected))
        self.assertEqual(len(clean), 9900)
        self.assertEqual(len(set(expected.values())), 10)
        self.assertEqual(validate(rows)[1]['invalid_rows'], 0)
    def test_small_fixture_rejected(self):
        with self.assertRaises(ValueError): inject_demo_errors(generate_visits(10))

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        self.rows = generate_visits(200)
        replace_visits(self.conn, self.rows)
    def tearDown(self): self.conn.close()
    def test_round_trip(self): self.assertEqual(len(analytics(self.conn)['rows']), 200)
    def test_summary_totals(self):
        self.assertEqual(sum(r['visits'] for r in analytics(self.conn)['summary']), 200)
    def test_filter(self):
        results = analytics(self.conn, ['Emergency'])
        expected = [r for r in self.rows if r['department'] == 'Emergency']
        self.assertEqual(len(results['rows']), len(expected))
        self.assertAlmostEqual(results['summary'][0]['avg_wait_minutes'],
                               sum(r['wait_minutes'] for r in expected)/len(expected), places=2)
    def test_empty_selection(self): self.assertEqual(analytics(self.conn, [])['rows'], [])
    def test_parameterized_query(self):
        self.assertEqual(analytics(self.conn, ["Emergency'); DROP TABLE visits; --"])['rows'], [])
        self.assertEqual(len(analytics(self.conn)['rows']), 200)
    def test_invalid_replace_preserves_data(self):
        with self.assertRaises(ValueError): replace_visits(self.conn, [{'visit_id': 'bad'}])
        self.assertEqual(len(analytics(self.conn)['rows']), 200)
    def test_replace_does_not_append(self):
        replace_visits(self.conn, self.rows[:10])
        self.assertEqual(len(analytics(self.conn)['rows']), 10)
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'test.sqlite'
            conn = connect(path)
            replace_visits(conn, self.rows)
            conn.close()
            conn = connect(path)
            try: self.assertEqual(len(analytics(conn)['rows']), 200)
            finally: conn.close()
    def test_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-m', 'hospital_data', '--count', '200',
                                    '--demo-errors', '--output', folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['accepted_rows'], 100)
            self.assertTrue((Path(folder)/'visits.sqlite').exists())
            again = subprocess.run([sys.executable, '-m', 'hospital_data', '--output', folder], capture_output=True)
            self.assertNotEqual(again.returncode, 0)

if __name__ == '__main__': unittest.main()
