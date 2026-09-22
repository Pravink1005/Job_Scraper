from pathlib import Path
import csv


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "csv_output"
    / "unified_jobs.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "ml"
    / "production_labeling.csv"
)


# ============================================================
# LOAD PRODUCTION JOBS
# ============================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    jobs = list(csv.DictReader(file))


# ============================================================
# CREATE LABELING DATASET
# ============================================================

rows = []

for job in jobs:

    rows.append(
        {
            "job_id": job.get(
                "job_id",
                ""
            ),

            "source": job.get(
                "source",
                ""
            ),

            "title": job.get(
                "title",
                ""
            ),

            "full_description": job.get(
                "full_description",
                ""
            ),

            "model_degree": job.get(
                "degree_required",
                "Not Specified"
            ),

            "model_specialization": job.get(
                "specialization_required",
                "Not Specified"
            ),

            "actual_degree": "",

            "actual_specialization": "",
        }
    )


# ============================================================
# WRITE FILE
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "job_id",
            "source",
            "title",
            "full_description",
            "model_degree",
            "model_specialization",
            "actual_degree",
            "actual_specialization",
        ]
    )

    writer.writeheader()
    writer.writerows(rows)


print("=" * 80)
print("PRODUCTION LABELING DATASET CREATED")
print("=" * 80)

print(
    f"Jobs exported : {len(rows)}"
)

print(
    f"Output file   : {OUTPUT_FILE}"
)

print()
print(
    "Next step:"
)

print(
    "Fill actual_degree and actual_specialization "
    "for each production job."
)

print("=" * 80)