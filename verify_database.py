import sqlite3

DB_PATH = "csv_output/jobs.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

print("=" * 70)
print("DATABASE VERIFICATION")
print("=" * 70)

# ------------------------------------------------------------
# Total rows
# ------------------------------------------------------------

cursor.execute("SELECT COUNT(*) FROM jobs")
total = cursor.fetchone()[0]

print(f"\nTotal jobs: {total}")

# ------------------------------------------------------------
# Source counts
# ------------------------------------------------------------

print("\nJobs by source:")

cursor.execute("""
    SELECT source, COUNT(*)
    FROM jobs
    GROUP BY source
    ORDER BY source
""")

for source, count in cursor.fetchall():
    print(f"  {source}: {count}")

# ------------------------------------------------------------
# Specific repaired records
# ------------------------------------------------------------

print("\nRepaired records:")

cursor.execute("""
    SELECT
        company,
        city,
        state,
        country,
        degree_required
    FROM jobs
    WHERE company IN (
        'Andaz',
        'Elementalent Technologies',
        'Public Health Career',
        'Revantage, A Blackstone Portfolio Company'
    )
    ORDER BY company
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

# ------------------------------------------------------------
# Bad education check
# ------------------------------------------------------------

cursor.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE degree_required LIKE '%(?:%'
       OR degree_required LIKE '%)?%'
       OR degree_required LIKE '%\\.%'
""")

bad_education = cursor.fetchone()[0]

print(
    f"\nEducation regex contamination: "
    f"{bad_education}"
)

# ------------------------------------------------------------
# LinkedIn metadata check
# ------------------------------------------------------------

cursor.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE source = 'LinkedIn'
      AND (
          city LIKE '%minutes ago%'
          OR city LIKE '%hours ago%'
          OR city LIKE '%days ago%'
          OR city LIKE '%applicants%'
          OR city LIKE '%See who%'
      )
""")

bad_location = cursor.fetchone()[0]

print(
    f"LinkedIn metadata in city: "
    f"{bad_location}"
)

# ------------------------------------------------------------
# Missing job IDs
# ------------------------------------------------------------

cursor.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE job_id IS NULL
       OR TRIM(job_id) = ''
""")

missing_ids = cursor.fetchone()[0]

print(
    f"Missing job IDs: "
    f"{missing_ids}"
)

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

print("\n" + "=" * 70)

if (
    total == 141
    and bad_education == 0
    and bad_location == 0
    and missing_ids == 0
):
    print("DATABASE VERIFICATION PASSED")
else:
    print("DATABASE VERIFICATION HAS WARNINGS")

print("=" * 70)

connection.close()