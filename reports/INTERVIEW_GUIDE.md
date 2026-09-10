# Explaining Hospital Data Lab

## A 30-second introduction

“I built a Python pipeline and Streamlit dashboard for experimenting with hospital-style data without using real patient records. It generates 10,000 fictional visits across five departments, applies ten validation rules, quarantines bad rows, and loads accepted data into SQLite for reporting. In a controlled test with 100 deliberately corrupted rows, it identified all 100 and retained the other 9,900. The project includes 42 automated tests.”

## Why these choices?

- **Seeded generation:** the same inputs reproduce the same rows, so bugs and benchmark results are easier to investigate.
- **Independent validation:** the validator checks field values and timestamp relationships rather than trusting the generator.
- **Quarantine:** inconsistent rows remain visible in the report but cannot distort the accepted-record analytics.
- **SQLite:** local persistence and SQL aggregation without a separate database server. Parameter binding separates filter values from SQL syntax.
- **Transactions:** replacement data is validated first; inserts and deletion are grouped in a transaction.
- **Streamlit:** provides filters, charts and downloads around the Python pipeline.

## Be precise about the numbers

- 10,000 = the measured sample size, not users or actual hospital encounters.
- 5 = department categories in the model.
- 10 = rule categories, not ten statistical privacy guarantees.
- 100/100 = deliberately corrupted rows detected in one controlled fixture.
- 42 = automated test methods, including four dashboard tests.
- Approximately 0.418 seconds = median total generation, validation and in-memory database/analytics time across five local runs. It excludes disk/CSV export and is hardware-dependent.

## What this does not establish

The fictional data has not been compared with a real hospital distribution. There is no clinical accuracy, measured hospital efficiency improvement, deployed user base, or privacy certification. The generation rules are deliberately simple and do not train or call an AI model.

## Demonstrate it in an interview

1. Start the dashboard and show the 10,000 accepted visits.
2. Toggle the defect demo: 100 quarantined, 9,900 accepted.
3. Open Data quality and explain why one row can violate multiple rules.
4. Filter to one department and export its accepted visits.
5. Point to one validator test and explain its input and expected outcome.
6. Explain why the benchmark uses repeated runs and reports a median.

## Next improvements worth discussing

Add configurable distributions and correlation rules, stream larger datasets in batches, validate imported synthetic CSV files, and compare distributions against a public synthetic benchmark. These are future ideas, not implemented features.
