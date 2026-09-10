# Hospital Data Lab

A Python data-engineering project that generates fictional hospital visits, quarantines inconsistent records, and explores accepted data through SQLite queries and a Streamlit dashboard.

**10,000 sample visits · 5 departments · 10 validation rules · 42 automated tests**

Built to demonstrate reproducible data generation, data-quality checks, SQL analytics and an interactive reporting workflow. This is an independent personal project. It does not represent work deployed at a hospital.

## Start the dashboard

Python 3.11 or newer recommended. From this folder, on macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, use `py -m venv .venv` and `.venv\Scripts\activate` in Command Prompt, then run the same pip and Streamlit commands. Open the local URL printed by Streamlit, usually `http://localhost:8501`.

The dashboard starts with 10,000 accepted visits. Toggle **Inject 100 demo defects** to see 100 rows quarantined and 9,900 retained. Change the seed, dataset size and department filters; inspect validation issues and download CSV or JSON results.

No account, API key, model download, or external dataset is needed. Python packages are downloaded during installation; generation itself is local.

## What the application does

1. **Generate:** use a local seeded random-number generator to create visit IDs, departments, ages and timestamps.
2. **Validate:** check schemas, IDs, categories, numeric bounds, timestamp validity, chronology and duration consistency.
3. **Quarantine:** keep rejected rows out of operational analytics, preserving row indices and readable reasons in a report.
4. **Store:** load accepted records into an indexed SQLite table in a transaction. Reject invalid replacement data before modifying the database.
5. **Analyze:** calculate visit volume, average wait and average stay by department, plus daily arrival counts, using parameterized SQL.
6. **Explore:** filter departments, compare charts, inspect records and export data from the dashboard.

The dashboard uses an in-memory SQLite database isolated to each run. The CLI writes a persistent SQLite database and export files to disk.

## Reproduce the included sample

```sh
python -m hospital_data --count 10000 --seed 42 --demo-errors --output output
python -m unittest discover -s tests -v
python benchmark.py
```

The core CLI and benchmark use only Python's standard library. The full test suite also exercises Streamlit, so install requirements before running it.

The CLI produces:

| File | Contents |
|---|---|
| `visits.csv` | All generated rows, including deliberately injected defects when requested |
| `accepted.csv` | Validated rows retained for analytics |
| `visits.sqlite` | Indexed, persistent database containing accepted rows |
| `validation.json` | Rejected row indices, rule counts and individual issues |
| `department_summary.json` | SQL aggregates by department |
| `run.json` | Configuration, counts and local phase timings |

Choose a new output directory for another run, or explicitly use `--overwrite`. The included `sample_output/` is a completed 10,000-row defect-demo run.

## Measured results

See `reports/benchmark.json` for five local timing samples, medians and environment details. Timings measure generation, validation, and in-memory SQLite loading/querying; SQLite loading validates accepted records a second time. CSV export and disk persistence are not included in that benchmark.

In the controlled fixture, **100 of 100 injected invalid rows were detected**, with **zero additional rows flagged**; **9,900 records** were accepted. Ten rows were modified in each of ten defect categories. These are results for a known fixture, not a claim of 100% accuracy on arbitrary hospital data.

All **42 unittest tests passed**, including dashboard interactions, CSV round-trips, deterministic generation, invalid inputs, database persistence, parameterized queries and rejection of invalid replacements. CI runs the suite after upload to GitHub.

## Data dictionary

| Column | Type | Meaning |
|---|---|---|
| `visit_id` | Text | Synthetic identifier, `SYN-` plus seven digits |
| `department` | Text | Emergency, Cardiology, Orthopedics, Imaging or General Medicine |
| `age` | Integer | Fictional age; generator uses 18–95 |
| `arrival_at` | Text | Arrival, formatted `YYYY-MM-DDTHH:MM` |
| `seen_at` | Text | Simulated first contact after waiting |
| `discharged_at` | Text | Simulated end of the visit |
| `wait_minutes` | Integer | Minutes from arrival to first contact |
| `stay_minutes` | Integer | Minutes from arrival to discharge, including wait |

Arrivals are uniformly sampled across 2025; discharge can occur in 2026 for late-year arrivals. Times are timezone-naive. Department-specific wait and treatment ranges are invented and documented in `hospital_data/core.py`. They are not estimates of real performance.

## Validation contract

There are ten rule categories:

- Exact columns and nonmissing values
- Synthetic ID format
- Duplicate IDs (later occurrences are rejected; the first occurrence reserves the ID even if it has another defect)
- Allowed department
- Integer age from 0 to 120
- Valid timestamp format and calendar date
- Arrival ≤ seen ≤ discharge
- Integer wait from 0 to 10,080 minutes
- Integer stay from 0 to 525,600 minutes
- Durations consistent with timestamps

The validator accepts integer CSV strings and normalizes them. Floats and booleans are rejected for integer fields. A row may violate several rules, so rule-violation totals can exceed the rejected-row count. CSV line numbers include the header; internal row indices begin at zero.

## Scope and limitations

All records come from invented rules. No patient records, names, addresses, health-card numbers or real operational data are used. This is not an anonymization system: it does not consume private records or prove that transformed records are safe to share.

This project is **not clinically validated, privacy-certified, an AI agent, or a predictive model**. It does not estimate treatment outcomes, staffing needs or real hospital performance. Passing the quality checks means structural consistency under the documented rules. The generator does not model correlated medical events or real-world case mixes.

Dataset size is bounded at 100,000 rows in the CLI and 25,000 in the dashboard to keep local runs manageable. CSV previews show the first 500 filtered rows; exports contain every matching accepted row. SQL mutations should go through the validated application API; direct external writes to SQLite can bypass some application checks.

## Project files

- `hospital_data/core.py`: generation, CSV serialization and controlled defects
- `hospital_data/validation.py`: row validation and reports
- `hospital_data/database.py`: database schema, validated loading and SQL analytics
- `hospital_data/__main__.py`: command-line pipeline
- `app.py`: interactive dashboard
- `tests/`: pipeline and dashboard regression tests
- `benchmark.py`: repeatable performance experiment
- `reports/`: measured results and demonstration evidence
- `sample_output/`: generated dataset and outputs

## Technical references

- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)

## License

MIT. See `LICENSE`.
