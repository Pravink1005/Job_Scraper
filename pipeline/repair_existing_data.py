
import csv
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\job_scraper_pipeline")
CSV_PATH = ROOT / "csv_output" / "unified_jobs.csv"
DB_PATH = ROOT / "csv_output" / "jobs.db"

# -----------------------------
# Backup CSV
# -----------------------------
backup_csv = CSV_PATH.with_name("unified_jobs_backup_before_location_fix.csv")
backup_csv.write_bytes(CSV_PATH.read_bytes())

# -----------------------------
# Read CSV
# -----------------------------
with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

fixed = 0

for row in rows:
    if row.get("country", "").strip() == "Haryana, India":
        row["city"] = row.get("city", "").strip() or "Not Specified"
        row["state"] = "Haryana"
        row["country"] = "India"
        fixed += 1

# -----------------------------
# Write CSV
# -----------------------------
temp_csv = CSV_PATH.with_suffix(".tmp")

with temp_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

temp_csv.replace(CSV_PATH)

print(f"CSV rows: {len(rows)}")
print(f"Rows fixed: {fixed}")

# -----------------------------
# Update SQLite
# -----------------------------
conn = sqlite3.connect(DB_PATH)

try:
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET city = ?,
            state = ?,
            country = ?
        WHERE country = ?
    """, (
        "Not Specified",
        "Haryana",
        "India",
        "Haryana, India"
    ))

    sqlite_fixed = cursor.rowcount
    conn.commit()

    print(f"SQLite rows fixed: {sqlite_fixed}")

finally:
    conn.close()

print()
print("LOCATION REPAIR COMPLETE")
