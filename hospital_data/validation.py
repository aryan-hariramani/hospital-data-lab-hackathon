"""Independent structural and consistency checks with row-level quarantine."""
from collections import Counter
from datetime import datetime
import re
from .core import FIELDS, DEPARTMENTS

RULES = {
    "schema": "Exact required columns and no missing values",
    "identifier": "Visit ID matches SYN- followed by seven digits",
    "duplicate": "Visit ID has not appeared in a previous row",
    "department": "Department is one of five supported categories",
    "age": "Age is a whole number from 0 to 120",
    "timestamp": "Timestamps use valid YYYY-MM-DDTHH:MM format",
    "chronology": "Arrival <= seen <= discharge",
    "wait": "Wait is a whole number from 0 to 10080 minutes",
    "stay": "Stay is a whole number from 0 to 525600 minutes",
    "duration": "Wait and stay equal their timestamp differences",
}

def integer(value):
    # CSV strings are accepted; floats and booleans are deliberately rejected.
    if type(value) is int: return value
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value): return int(value)
    raise ValueError("Expected integer")

def validate(rows):
    seen = set()
    issues = []
    valid = []
    invalid_indices = []
    for index, row in enumerate(rows):
        codes = set()
        if set(row) != set(FIELDS) or any(row.get(f) is None or row.get(f) == "" for f in FIELDS):
            codes.add("schema")
        visit_id = row.get("visit_id")
        if not isinstance(visit_id, str) or re.fullmatch(r"SYN-\d{7}", visit_id) is None:
            codes.add("identifier")
        else:
            if visit_id in seen: codes.add("duplicate")
            seen.add(visit_id)
        if not isinstance(row.get("department"), str) or row.get("department") not in DEPARTMENTS:
            codes.add("department")
        normalized = dict(row)
        for field, code, low, high in (("age", "age", 0, 120),
                                      ("wait_minutes", "wait", 0, 10080),
                                      ("stay_minutes", "stay", 0, 525600)):
            try:
                val = integer(row.get(field))
                normalized[field] = val
                if not low <= val <= high: codes.add(code)
            except (ValueError, TypeError): codes.add(code)
        times = {}
        for field in ("arrival_at", "seen_at", "discharged_at"):
            try:
                value = row.get(field)
                if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", value) is None:
                    raise ValueError("Invalid timestamp format")
                times[field] = datetime.strptime(value, "%Y-%m-%dT%H:%M")
            except (ValueError, TypeError): codes.add("timestamp")
        if len(times) == 3:
            a, s, d = (times[f] for f in ("arrival_at", "seen_at", "discharged_at"))
            if not a <= s <= d: codes.add("chronology")
            if "wait" not in codes and normalized["wait_minutes"] != (s - a).total_seconds() / 60:
                codes.add("duration")
            if "stay" not in codes and normalized["stay_minutes"] != (d - a).total_seconds() / 60:
                codes.add("duration")
        if codes:
            invalid_indices.append(index)
            for code in sorted(codes):
                issues.append({"row_index": index, "csv_line": index + 2,
                               "visit_id": str(visit_id), "rule": code, "message": RULES[code]})
        else:
            valid.append(normalized)
    counts = Counter(issue["rule"] for issue in issues)
    report = {"total_rows": len(rows), "valid_rows": len(valid), "invalid_rows": len(invalid_indices),
              "issue_count": len(issues), "rule_counts": dict(sorted(counts.items())),
              "invalid_indices": invalid_indices, "issues": issues}
    return valid, report
