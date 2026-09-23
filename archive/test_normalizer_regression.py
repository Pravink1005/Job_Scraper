import csv
from pathlib import Path

from pipeline.normalizer import normalize


CSV_PATH = Path("csv_output/unified_jobs.csv")


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def comparable(value):
    """
    Convert values into a comparable representation.

    Empty strings and 'Not Specified' are treated as equivalent
    because they both mean that the field has no value.
    """

    value = clean(value)

    if value.lower() in {
        "",
        "not specified",
        "not_specified",
        "none",
        "null",
    }:
        return ""

    return value


def main():

    print("=" * 70)
    print("NORMALIZER REGRESSION TEST")
    print("=" * 70)

    if not CSV_PATH.exists():
        print(f"[ERROR] CSV not found: {CSV_PATH}")
        return

    with open(
        CSV_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)
        rows = list(reader)

    print()
    print(f"Rows loaded: {len(rows)}")

    if not rows:
        print("[ERROR] No rows found.")
        return

    changed_rows = 0
    changed_fields = 0
    problems = []

    fields_to_test = [
        "company",
        "city",
        "state",
        "country",
        "degree_required",
        "specialization_required",
        "skills",
    ]

    for index, row in enumerate(rows, start=1):

        source = clean(row.get("source"))

        # ----------------------------------------------------------
        # Rebuild the raw job using ALL relevant existing fields.
        # ----------------------------------------------------------

        location_parts = [
            clean(row.get("city")),
            clean(row.get("state")),
            clean(row.get("country")),
        ]

        location = ", ".join(
            part for part in location_parts if part
        )

        raw_job = {
            "job_id": clean(row.get("job_id")),

            "job_title": clean(row.get("title")),

            "company_name": clean(row.get("company")),

            "location": location,

            "job_description": clean(
                row.get("full_description")
            ),

            "posted_date": clean(
                row.get("posted_time")
            ),

            "education": clean(
                row.get("degree_required")
            ),

            "specialization": clean(
                row.get("specialization_required")
            ),

            "specialization_required": clean(
                row.get("specialization_required")
            ),

            "skills": clean(
                row.get("skills")
            ),

            "job_url": clean(
                row.get("link")
            ),
        }

        # ----------------------------------------------------------
        # Run normalizer
        # ----------------------------------------------------------

        try:

            normalized = normalize(
                source,
                raw_job
            )

        except Exception as error:

            problems.append(
                f"Row {index} | "
                f"job_id={row.get('job_id')} | "
                f"ERROR: {error}"
            )

            continue

        # ----------------------------------------------------------
        # Compare fields
        # ----------------------------------------------------------

        row_changed = False

        for field in fields_to_test:

            old_value = comparable(
                row.get(field)
            )

            new_value = comparable(
                getattr(
                    normalized,
                    field,
                    ""
                )
            )

            if old_value != new_value:

                row_changed = True
                changed_fields += 1

                if len(problems) < 50:

                    problems.append(
                        f"Row {index} | "
                        f"{row.get('job_id')} | "
                        f"{field}: "
                        f"{row.get(field)!r} -> "
                        f"{getattr(normalized, field, '')!r}"
                    )

        if row_changed:
            changed_rows += 1

    # --------------------------------------------------------------
    # Results
    # --------------------------------------------------------------

    print()
    print("-" * 70)
    print("REGRESSION RESULTS")
    print("-" * 70)

    print(f"Rows tested       : {len(rows)}")
    print(f"Rows changed      : {changed_rows}")
    print(f"Fields changed    : {changed_fields}")
    print(f"Problems detected : {len(problems)}")

    if problems:

        print()
        print("-" * 70)
        print("CHANGES / PROBLEMS")
        print("-" * 70)

        for problem in problems:
            print(problem)

        if len(problems) >= 50:
            print()
            print("Only the first 50 changes/problems are shown.")

    print()
    print("=" * 70)

    if not problems:

        print("REGRESSION TEST PASSED")
        print()
        print(
            "The new normalizer preserves the existing "
            "141-row dataset."
        )

    else:

        print("REGRESSION TEST FOUND CHANGES")
        print()
        print(
            "DO NOT run main.py yet."
        )
        print(
            "Review the changes above before enabling "
            "production normalization."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()