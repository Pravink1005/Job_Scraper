import pandas as pd
from pathlib import Path

CSV_PATH = Path("csv_output/unified_jobs.csv")

COMPANY = "Revantage, A Blackstone Portfolio Company"


def main():

    print("=" * 70)
    print("FIX REVANTAGE LOCATION IN CSV")
    print("=" * 70)

    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found: {CSV_PATH}")
        return

    df = pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False,
    )

    mask = (
        df["company"].astype(str).str.strip()
        == COMPANY
    )

    count = int(mask.sum())

    print(f"\nMatching rows: {count}")

    if count == 0:
        print("Revantage record not found.")
        return

    print("\nBefore:")

    print(
        df.loc[
            mask,
            [
                "company",
                "city",
                "state",
                "country",
            ],
        ].to_string(index=False)
    )

    # Correct only the location fields.
    df.loc[mask, "city"] = "Bengaluru"
    df.loc[mask, "state"] = "Karnataka"
    df.loc[mask, "country"] = "India"

    df.to_csv(
        CSV_PATH,
        index=False,
    )

    print("\nAfter:")

    print(
        df.loc[
            mask,
            [
                "company",
                "city",
                "state",
                "country",
            ],
        ].to_string(index=False)
    )

    print("\nRows in CSV:", len(df))

    print("\n" + "=" * 70)
    print("CSV REVANTAGE FIX COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()