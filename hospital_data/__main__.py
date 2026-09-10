"""Generate a reproducible dataset, quarantine defects, and export SQLite analytics."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from .core import generate_visits, inject_demo_errors, csv_text
from .validation import validate
from .database import connect, replace_visits, analytics

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--demo-errors", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacement of existing output directory contents")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite:
        parser.error("Output directory is not empty; choose another directory or use --overwrite")
    start = perf_counter()
    try: rows = generate_visits(args.count, args.seed)
    except ValueError as exc: parser.error(str(exc))
    generated = perf_counter()
    expected = {}
    if args.demo_errors:
        try: rows, expected = inject_demo_errors(rows)
        except ValueError as exc: parser.error(str(exc))
    clean, report = validate(rows)
    validated = perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    conn = connect(args.output / "visits.sqlite")
    try:
        replace_visits(conn, clean)
        summary = analytics(conn)["summary"]
    finally: conn.close()
    stored = perf_counter()
    (args.output / "visits.csv").write_text(csv_text(rows))
    (args.output / "accepted.csv").write_text(csv_text(clean))
    (args.output / "validation.json").write_text(json.dumps(report, indent=2))
    (args.output / "department_summary.json").write_text(json.dumps(summary, indent=2))
    detected = set(report["invalid_indices"])
    result = {"seed": args.seed, "requested_rows": args.count,
              "accepted_rows": len(clean), "quarantined_rows": report["invalid_rows"],
              "generation_seconds": round(generated-start, 6),
              "validation_seconds": round(validated-generated, 6),
              "database_and_analytics_seconds": round(stored-validated, 6),
              "known_injected_rows": len(expected), "injected_rows_detected": len(detected & set(expected)),
              "other_rows_flagged": len(detected - set(expected))}
    (args.output / "run.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
