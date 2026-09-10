"""Interactive exploration of fictional visits and data-quality results."""
import json
import pandas as pd
import streamlit as st
from hospital_data.core import DEPARTMENTS, generate_visits, inject_demo_errors, csv_text
from hospital_data.validation import validate, RULES
from hospital_data.database import connect, replace_visits, analytics

st.set_page_config(page_title="Hospital Data Lab", page_icon="🏥", layout="wide")
st.title("Hospital Data Lab")
st.caption("Generate fictional visits. Find data defects. Explore validated records.")
st.info("Synthetic demonstration only · No real patient records · Not clinically validated")
with st.sidebar:
    st.header("Dataset settings")
    count = st.select_slider("Visits", options=[1000, 5000, 10000, 25000], value=10000)
    seed = st.number_input("Random seed", min_value=0, max_value=1000000, value=42)
    corrupted = st.toggle("Inject 100 demo defects", value=False)
    st.caption("Ten rows per defect category; generated data remains reproducible.")
    selected = st.multiselect("Departments", list(DEPARTMENTS), default=list(DEPARTMENTS))

@st.cache_data(show_spinner=False)
def prepare(count, seed, corrupted):
    rows = generate_visits(count, seed)
    if corrupted: rows, _ = inject_demo_errors(rows)
    clean, report = validate(rows)
    return rows, clean, report

rows, clean, report = prepare(count, seed, corrupted)
conn = connect()
try:
    replace_visits(conn, clean)
    results = analytics(conn, selected)
finally:
    conn.close()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Generated visits", f"{len(rows):,}")
c2.metric("Accepted visits", f"{len(clean):,}")
c3.metric("Quarantined visits", f"{report['invalid_rows']:,}")
c4.metric("Validation rules", str(len(RULES)))
st.caption("Validation totals cover the full dataset. Department filters apply to accepted-record analytics below.")
overview, quality, records, method = st.tabs(["Operations overview", "Data quality", "Explore & export", "How it works"])
with overview:
    st.subheader("Department activity")
    if not results["rows"]:
        st.warning("Select at least one department to display accepted visits.")
    else:
        frame = pd.DataFrame(results["summary"])
        left, right = st.columns(2)
        with left:
            st.markdown("**Visit volume**")
            st.bar_chart(frame.set_index("department")[["visits"]], color="#0891b2")
        with right:
            st.markdown("**Average wait · minutes**")
            st.bar_chart(frame.set_index("department")[["avg_wait_minutes"]], color="#7c3aed")
        st.markdown("**Daily arrivals**")
        daily = pd.DataFrame(results["daily"])
        daily["day"] = pd.to_datetime(daily["day"])
        daily = daily.set_index("day").reindex(pd.date_range("2025-01-01", "2025-12-31"), fill_value=0)
        st.line_chart(daily, color="#0891b2")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Patterns come from invented generator settings, not observed hospital demand.")
with quality:
    st.subheader("Validation & quarantine")
    if report["invalid_rows"]:
        st.warning(f"{report['invalid_rows']} rows excluded from analytics; {report['issue_count']} rule violations found.")
        st.dataframe(pd.DataFrame(report["issues"]), hide_index=True, width="stretch")
        st.bar_chart(pd.DataFrame(list(report["rule_counts"].items()), columns=["Rule", "Violations"]).set_index("Rule"))
    else:
        st.success("All generated visits passed the structural and consistency checks.")
    st.caption("A row may violate multiple rules. Passing checks does not establish clinical realism or certify privacy.")
    st.download_button("Download validation report", json.dumps(report, indent=2), "validation.json", "application/json")
with records:
    st.subheader("Accepted visits")
    st.write(f"{len(results['rows']):,} visits match your department selection.")
    st.dataframe(pd.DataFrame(results["rows"][:500]), hide_index=True, width="stretch")
    st.caption("Preview limited to 500 rows; filtered download contains all matching accepted visits.")
    st.download_button("Download filtered accepted CSV", csv_text(results["rows"]), "accepted_visits.csv", "text/csv")
    st.download_button("Download full generated CSV", csv_text(rows), "generated_visits.csv", "text/csv")
with method:
    st.markdown("""
### Reproducible data-quality experiments
1. Generate visits using a local seeded random-number generator and invented ranges.
2. Optionally inject 100 defects into distinct rows.
3. Check each row and quarantine those that fail.
4. Load accepted visits into SQLite and query aggregates with parameterized SQL.

**Scope:** five departments, adult ages 18–95, and arrivals during 2025. Stay includes waiting time. Timestamps are timezone-naive simulation times.

No names, addresses, medical record numbers, external datasets, API keys, or model training are used. This is a rule-based data engineering project, not an AI agent or a clinical simulation.
""")
    st.dataframe(pd.DataFrame(list(RULES.items()), columns=["Rule", "Check"]), hide_index=True, width="stretch")
