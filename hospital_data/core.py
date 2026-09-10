"""Deterministic toy data. No patient data, trained model, or network requests."""
import csv
import io
import random
from datetime import datetime, timedelta

FIELDS = ("visit_id", "department", "age", "arrival_at", "seen_at", "discharged_at",
          "wait_minutes", "stay_minutes")
# Invented ranges for demonstrations, not estimates of real hospital operations.
DEPARTMENTS = {
    "Emergency": (10, 240, 30, 480),
    "Cardiology": (5, 90, 45, 180),
    "Orthopedics": (5, 120, 30, 180),
    "Imaging": (5, 75, 15, 90),
    "General Medicine": (10, 150, 30, 240),
}

def generate_visits(count=10000, seed=42):
    if type(count) is not int or not 1 <= count <= 100000:
        raise ValueError("count must be an integer between 1 and 100,000")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    rows = []
    start = datetime(2025, 1, 1)
    for i in range(count):
        department = rng.choice(list(DEPARTMENTS))
        low_w, high_w, low_s, high_s = DEPARTMENTS[department]
        wait = rng.randint(low_w, high_w)
        stay = wait + rng.randint(low_s, high_s)
        arrival = start + timedelta(minutes=rng.randrange(365 * 24 * 60))
        rows.append(dict(zip(FIELDS, (
            f"SYN-{i + 1:07d}", department, rng.randint(18, 95),
            arrival.isoformat(timespec="minutes"),
            (arrival + timedelta(minutes=wait)).isoformat(timespec="minutes"),
            (arrival + timedelta(minutes=stay)).isoformat(timespec="minutes"), wait, stay))))
    return rows

def csv_text(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()

def inject_demo_errors(rows):
    """Inject 100 known bad rows across ten categories; leave inputs untouched.

    Returns corrupted copies and zero-based row indices with injected defects.
    This is a controlled fixture, not a model of real-world error rates.
    """
    if len(rows) < 200:
        raise ValueError("Error demo requires at least 200 visits")
    copies = [dict(row) for row in rows]
    categories = ("missing", "identifier", "duplicate", "department", "age",
                  "timestamp", "chronology", "wait", "stay", "duration")
    expected = {}
    for k, category in enumerate(categories):
        for j in range(10):
            index = 100 + k * 10 + j
            row = copies[index]
            if category == "missing": row["department"] = ""
            elif category == "identifier": row["visit_id"] = "bad-id"
            elif category == "duplicate": row["visit_id"] = copies[j]["visit_id"]
            elif category == "department": row["department"] = "Unknown"
            elif category == "age": row["age"] = -1
            elif category == "timestamp": row["arrival_at"] = "2025-02-30T12:00"
            elif category == "chronology": row["discharged_at"] = "2024-01-01T00:00"
            elif category == "wait": row["wait_minutes"] = -1
            elif category == "stay": row["stay_minutes"] = -1
            elif category == "duration": row["wait_minutes"] += 1
            expected[index] = category
    return copies, expected
