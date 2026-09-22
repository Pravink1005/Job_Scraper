import csv
import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

CSV_PATH = Path("csv_output/unified_jobs.csv")
DB_PATH = Path("csv_output/jobs.db")


# ============================================================
# DATABASE SCHEMA
# ============================================================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    source TEXT,
    title TEXT,
    company TEXT,
    category TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    min_experience_years TEXT,
    max_experience_years TEXT,
    salary TEXT,
    skills TEXT,
    degree_required TEXT,
    specialization_required TEXT,
    posted_time TEXT,
    collected_at TEXT,
    link TEXT,
    full_description TEXT
)
"""


# ============================================================
# DATABASE CONNECTION
# ============================================================

def create_database():

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(CREATE_TABLE_SQL)

    connection.commit()

    return connection


# ============================================================
# IMPORT CSV → SQLITE
# ============================================================

def import_csv_to_database():

    if not CSV_PATH.exists():
        print(f"[ERROR] CSV file not found: {CSV_PATH}")
        return

    print("=" * 70)
    print("CSV → SQLITE DATABASE IMPORT")
    print("=" * 70)

    print(f"CSV: {CSV_PATH}")
    print(f"Database: {DB_PATH}")
    print()

    connection = create_database()
    cursor = connection.cursor()

    inserted = 0
    updated = 0
    skipped = 0

    with open(
        CSV_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            job_id = (row.get("job_id") or "").strip()

            if not job_id:
                skipped += 1
                continue

            values = (
                job_id,
                row.get("source", "Not Specified"),
                row.get("title", "Not Specified"),
                row.get("company", "Not Specified"),
                row.get("category", "Not Specified"),
                row.get("city", "Not Specified"),
                row.get("state", "Not Specified"),
                row.get("country", "Not Specified"),
                row.get("min_experience_years", "Not Specified"),
                row.get("max_experience_years", "Not Specified"),
                row.get("salary", "Not specified"),
                row.get("skills", "Not specified"),
                row.get("degree_required", "Not Specified"),
                row.get("specialization_required", "Not Specified"),
                row.get("posted_time", "Not Specified"),
                row.get("collected_at", "Not Specified"),
                row.get("link", "Not Specified"),
                row.get("full_description", "Not Specified"),
            )

            cursor.execute(
                """
                INSERT INTO jobs (
                    job_id,
                    source,
                    title,
                    company,
                    category,
                    city,
                    state,
                    country,
                    min_experience_years,
                    max_experience_years,
                    salary,
                    skills,
                    degree_required,
                    specialization_required,
                    posted_time,
                    collected_at,
                    link,
                    full_description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(job_id)
                DO UPDATE SET
                    source = excluded.source,
                    title = excluded.title,
                    company = excluded.company,
                    category = excluded.category,
                    city = excluded.city,
                    state = excluded.state,
                    country = excluded.country,
                    min_experience_years = excluded.min_experience_years,
                    max_experience_years = excluded.max_experience_years,
                    salary = excluded.salary,
                    skills = excluded.skills,
                    degree_required = excluded.degree_required,
                    specialization_required = excluded.specialization_required,
                    posted_time = excluded.posted_time,
                    collected_at = excluded.collected_at,
                    link = excluded.link,
                    full_description = excluded.full_description
                """,
                values
            )

            if cursor.rowcount == 1:
                inserted += 1
            else:
                updated += 1

    connection.commit()

    # ========================================================
    # CREATE INDEXES
    # ========================================================

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)"
    )

    connection.commit()

    # ========================================================
    # DATABASE SUMMARY
    # ========================================================

    cursor.execute("SELECT COUNT(*) FROM jobs")

    total_jobs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT source, COUNT(*) FROM jobs GROUP BY source"
    )

    source_counts = cursor.fetchall()

    connection.close()

    print()
    print("=" * 70)
    print("SQLITE IMPORT COMPLETE")
    print("=" * 70)

    print(f"Rows processed : {inserted + updated + skipped}")
    print(f"Skipped        : {skipped}")
    print(f"Total jobs DB  : {total_jobs}")

    print()
    print("Jobs by source:")

    for source, count in source_counts:
        print(f"  {source}: {count}")

    print()
    print(f"SQLite database: {DB_PATH}")
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import_csv_to_database()