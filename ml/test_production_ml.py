from pathlib import Path
import sys
import csv


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "csv_output" / "unified_jobs.csv"
ML_DIR = BASE_DIR / "ml"

if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))


# ============================================================
# IMPORT EXISTING ML MODEL
# ============================================================

from ml_predictor import predict_job_details


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 80)
    print("PRODUCTION ML VALIDATION")
    print("=" * 80)

    print(f"CSV: {CSV_FILE}")
    print()

    if not CSV_FILE.exists():
        print("[ERROR] Production CSV not found.")
        return

    # --------------------------------------------------------
    # LOAD PRODUCTION DATA
    # --------------------------------------------------------

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)
        jobs = list(reader)

    print(f"Production jobs loaded: {len(jobs)}")
    print()

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    total = len(jobs)

    predicted_degree = 0
    predicted_specialization = 0

    not_specified_degree = 0
    not_specified_specialization = 0

    errors = 0

    # --------------------------------------------------------
    # TEST EACH JOB
    # --------------------------------------------------------

    print("-" * 80)
    print("JOB-BY-JOB ML PREDICTIONS")
    print("-" * 80)

    for index, job in enumerate(jobs, start=1):

        job_id = job.get("job_id", "Not Specified")
        title = job.get("title", "Not Specified")
        description = job.get("full_description", "")

        print()
        print(f"[{index}/{total}] {title}")
        print(f"Job ID       : {job_id}")

        if not description or description.strip().lower() in {
            "",
            "not specified",
            "n/a",
            "none",
            "null"
        }:
            print("Description  : Not usable")
            print("ML Result    : SKIPPED")
            continue

        try:

            result = predict_job_details(description)

            degree = result.get(
                "predicted_degree",
                "Not Specified"
            )

            specialization = result.get(
                "predicted_specialization",
                "Not Specified"
            )

            print(f"ML Degree    : {degree}")
            print(
                f"ML Specialization : "
                f"{specialization}"
            )

            if degree != "Not Specified":
                predicted_degree += 1
            else:
                not_specified_degree += 1

            if specialization != "Not Specified":
                predicted_specialization += 1
            else:
                not_specified_specialization += 1

        except Exception as error:

            errors += 1

            print(
                f"[ERROR] ML prediction failed: {error}"
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("PRODUCTION ML VALIDATION SUMMARY")
    print("=" * 80)

    print(f"Total production jobs       : {total}")
    print()

    print("DEGREE")
    print("-" * 40)
    print(
        f"Predicted                  : "
        f"{predicted_degree}"
    )
    print(
        f"Not Specified              : "
        f"{not_specified_degree}"
    )

    print()

    print("SPECIALIZATION")
    print("-" * 40)
    print(
        f"Predicted                  : "
        f"{predicted_specialization}"
    )
    print(
        f"Not Specified              : "
        f"{not_specified_specialization}"
    )

    print()

    print(f"Prediction errors           : {errors}")

    print()
    print("=" * 80)

    if errors == 0:
        print("PRODUCTION ML VALIDATION COMPLETED")
    else:
        print("PRODUCTION ML VALIDATION COMPLETED WITH ERRORS")

    print("=" * 80)


if __name__ == "__main__":
    main()