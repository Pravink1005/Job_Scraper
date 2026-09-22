from pathlib import Path
import pandas as pd


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = (
    BASE_DIR
    / "Degree_Prediction_Training_5000_Corrected.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Training dataset not found:\n{DATA_FILE}"
    )


data = pd.read_csv(DATA_FILE)


print("=" * 90)
print("TRAINING DATA ANALYSIS")
print("=" * 90)

print(f"Dataset: {DATA_FILE}")
print(f"Rows   : {len(data)}")
print(f"Columns: {len(data.columns)}")

print()
print("Columns:")
for column in data.columns:
    print(f"  - {column}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required = {
    "job_description",
    "degree",
    "specialization",
}

missing = required - set(data.columns)

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# DEGREE DISTRIBUTION
# ============================================================

print()
print("=" * 90)
print("DEGREE CLASS DISTRIBUTION")
print("=" * 90)

degree_counts = (
    data["degree"]
    .fillna("Not Specified")
    .astype(str)
    .value_counts()
)

for degree, count in degree_counts.items():

    percentage = (
        count / len(data) * 100
    )

    print(
        f"{degree:<40} "
        f"{count:>5} "
        f"({percentage:>6.2f}%)"
    )


# ============================================================
# SPECIALIZATION DISTRIBUTION
# ============================================================

print()
print("=" * 90)
print("SPECIALIZATION CLASS DISTRIBUTION")
print("=" * 90)

specialization_counts = (
    data["specialization"]
    .fillna("Not Specified")
    .astype(str)
    .value_counts()
)

for specialization, count in (
    specialization_counts.items()
):

    percentage = (
        count / len(data) * 100
    )

    print(
        f"{specialization:<40} "
        f"{count:>5} "
        f"({percentage:>6.2f}%)"
    )


# ============================================================
# DESCRIPTION QUALITY
# ============================================================

print()
print("=" * 90)
print("DESCRIPTION QUALITY")
print("=" * 90)

descriptions = (
    data["job_description"]
    .fillna("")
    .astype(str)
)

empty_descriptions = (
    descriptions.str.strip() == ""
).sum()

short_descriptions = (
    descriptions.str.len() < 100
).sum()

print(
    f"Empty descriptions       : "
    f"{empty_descriptions}"
)

print(
    f"Descriptions <100 chars  : "
    f"{short_descriptions}"
)

print(
    f"Average description size : "
    f"{descriptions.str.len().mean():.2f}"
)

print(
    f"Median description size  : "
    f"{descriptions.str.len().median():.2f}"
)


# ============================================================
# LABEL QUALITY
# ============================================================

print()
print("=" * 90)
print("LABEL QUALITY")
print("=" * 90)

print(
    f"Unique degree classes          : "
    f"{data['degree'].nunique()}"
)

print(
    f"Unique specialization classes  : "
    f"{data['specialization'].nunique()}"
)


# ============================================================
# RARE CLASSES
# ============================================================

print()
print("=" * 90)
print("RARE DEGREE CLASSES (<20 samples)")
print("=" * 90)

rare_degrees = degree_counts[
    degree_counts < 20
]

if len(rare_degrees) == 0:

    print("None")

else:

    for label, count in rare_degrees.items():
        print(f"{label:<40} {count}")


print()
print("=" * 90)
print("RARE SPECIALIZATION CLASSES (<20 samples)")
print("=" * 90)

rare_specializations = (
    specialization_counts[
        specialization_counts < 20
    ]
)

if len(rare_specializations) == 0:

    print("None")

else:

    for label, count in (
        rare_specializations.items()
    ):
        print(
            f"{label:<40} {count}"
        )


# ============================================================
# SAMPLE RECORDS
# ============================================================

print()
print("=" * 90)
print("SAMPLE TRAINING RECORDS")
print("=" * 90)

sample = data.sample(
    min(10, len(data)),
    random_state=42
)

for index, row in sample.iterrows():

    print()
    print(
        f"Degree         : "
        f"{row['degree']}"
    )

    print(
        f"Specialization : "
        f"{row['specialization']}"
    )

    description = str(
        row["job_description"]
    )

    print(
        f"Description    : "
        f"{description[:300]}"
    )


print()
print("=" * 90)
print("TRAINING DATA ANALYSIS COMPLETED")
print("=" * 90)