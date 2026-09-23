from pathlib import Path
import csv


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "production_labeling.csv"
OUTPUT_FILE = BASE_DIR / "production_review.csv"


# ============================================================
# LOAD LABELING FILE
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"File not found:\n{INPUT_FILE}"
    )


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    jobs = list(csv.DictReader(file))


# ============================================================
# CREATE REVIEW FILE
# ============================================================

review_rows = []

for job in jobs:

    review_rows.append(
        {
            "job_id": job.get("job_id", ""),
            "source": job.get("source", ""),
            "title": job.get("title", ""),

            "model_degree": job.get(
                "model_degree",
                "Not Specified"
            ),

            "model_specialization": job.get(
                "model_specialization",
                "Not Specified"
            ),

            "actual_degree": job.get(
                "actual_degree",
                ""
            ),

            "actual_specialization": job.get(
                "actual_specialization",
                ""
            ),

            "full_description": job.get(
                "full_description",
                ""
            ),
        }
    )


# ============================================================
# WRITE REVIEW FILE
# ============================================================

fieldnames = [
    "job_id",
    "source",
    "title",
    "model_degree",
    "model_specialization",
    "actual_degree",
    "actual_specialization",
    "full_description",
]


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(review_rows)


# ============================================================
# RESULT
# ============================================================

print("=" * 80)
print("PRODUCTION REVIEW FILE CREATED")
print("=" * 80)

print(
    f"Jobs exported : {len(review_rows)}"
)

print(
    f"Output file   : {OUTPUT_FILE}"
)

print()
print("Columns:")
for column in fieldnames:
    print(f"  - {column}")

print()
print("Fill these two columns:")
print("  actual_degree")
print("  actual_specialization")

print()
print(
    "Use 'Not Specified' when the job description "
    "does not clearly state the requirement."
)

print("=" * 80)