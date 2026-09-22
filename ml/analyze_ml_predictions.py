from pathlib import Path
import sys
import csv
import joblib


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = BASE_DIR / "csv_output" / "unified_jobs.csv"
ML_DIR = BASE_DIR / "ml"
MODEL_DIR = ML_DIR / "models"

if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))


# ============================================================
# EXISTING EXTRACTORS
# ============================================================

from ml_predictor import (
    extract_degree_text,
    extract_specialization_text,
    detect_explicit_degree,
    detect_explicit_specialization,
)


# ============================================================
# LOAD EXISTING MODELS
# ============================================================

degree_vectorizer = joblib.load(
    MODEL_DIR / "degree_vectorizer.pkl"
)

degree_model = joblib.load(
    MODEL_DIR / "degree_model.pkl"
)

specialization_vectorizer = joblib.load(
    MODEL_DIR / "specialization_vectorizer.pkl"
)

specialization_model = joblib.load(
    MODEL_DIR / "specialization_model.pkl"
)


# ============================================================
# LOAD PRODUCTION DATA
# ============================================================

if not CSV_FILE.exists():
    raise FileNotFoundError(
        f"Production CSV not found: {CSV_FILE}"
    )


with open(
    CSV_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    jobs = list(csv.DictReader(file))


# ============================================================
# ANALYSIS
# ============================================================

print("=" * 90)
print("ML PREDICTION QUALITY & CONFIDENCE ANALYSIS")
print("=" * 90)

print(f"Production jobs: {len(jobs)}")
print()


degree_rule_count = 0
degree_ml_count = 0
degree_low_confidence = 0

specialization_rule_count = 0
specialization_ml_count = 0
specialization_low_confidence = 0


degree_confidences = []
specialization_confidences = []


# ============================================================
# JOB ANALYSIS
# ============================================================

for index, job in enumerate(jobs, start=1):

    title = job.get(
        "title",
        "Not Specified"
    )

    job_id = job.get(
        "job_id",
        "Not Specified"
    )

    description = job.get(
        "full_description",
        ""
    )

    print("-" * 90)
    print(f"[{index}/{len(jobs)}] {title}")
    print(f"Job ID: {job_id}")

    if not description.strip():
        print("Description: Not available")
        continue

    # ========================================================
    # DEGREE
    # ========================================================

    explicit_degree = detect_explicit_degree(
        description
    )

    if explicit_degree:

        degree_rule_count += 1

        print(
            "Degree method       : RULE"
        )

        print(
            f"Degree prediction   : "
            f"{' / '.join(explicit_degree)}"
        )

    else:

        degree_text = extract_degree_text(
            description
        )

        if degree_text.strip():

            try:

                degree_vector = (
                    degree_vectorizer.transform(
                        [degree_text]
                    )
                )

                degree_probabilities = (
                    degree_model.predict_proba(
                        degree_vector
                    )[0]
                )

                degree_index = (
                    degree_probabilities.argmax()
                )

                degree_prediction = str(
                    degree_model.classes_[
                        degree_index
                    ]
                )

                degree_confidence = (
                    degree_probabilities[
                        degree_index
                    ] * 100
                )

                degree_confidences.append(
                    degree_confidence
                )

                print(
                    "Degree method       : ML"
                )

                print(
                    f"Degree prediction   : "
                    f"{degree_prediction}"
                )

                print(
                    f"Degree confidence   : "
                    f"{degree_confidence:.2f}%"
                )

                if degree_confidence >= 60:

                    degree_ml_count += 1

                else:

                    degree_low_confidence += 1

                    print(
                        "Degree status       : "
                        "LOW CONFIDENCE"
                    )

            except Exception as error:

                print(
                    f"Degree ML error: {error}"
                )

        else:

            print(
                "Degree method       : "
                "NO USABLE DEGREE TEXT"
            )

    # ========================================================
    # SPECIALIZATION
    # ========================================================

    explicit_specialization = (
        detect_explicit_specialization(
            description
        )
    )

    if explicit_specialization:

        specialization_rule_count += 1

        print(
            "Specialization method : RULE"
        )

        print(
            f"Specialization      : "
            f"{explicit_specialization[0]}"
        )

    else:

        specialization_text = (
            extract_specialization_text(
                description
            )
        )

        if specialization_text.strip():

            try:

                specialization_vector = (
                    specialization_vectorizer.transform(
                        [specialization_text]
                    )
                )

                specialization_probabilities = (
                    specialization_model.predict_proba(
                        specialization_vector
                    )[0]
                )

                specialization_index = (
                    specialization_probabilities.argmax()
                )

                specialization_prediction = str(
                    specialization_model.classes_[
                        specialization_index
                    ]
                )

                specialization_confidence = (
                    specialization_probabilities[
                        specialization_index
                    ] * 100
                )

                specialization_confidences.append(
                    specialization_confidence
                )

                print(
                    "Specialization method : ML"
                )

                print(
                    f"Specialization      : "
                    f"{specialization_prediction}"
                )

                print(
                    f"Specialization confidence : "
                    f"{specialization_confidence:.2f}%"
                )

                if specialization_confidence >= 60:

                    specialization_ml_count += 1

                else:

                    specialization_low_confidence += 1

                    print(
                        "Specialization status : "
                        "LOW CONFIDENCE"
                    )

            except Exception as error:

                print(
                    f"Specialization ML error: "
                    f"{error}"
                )

        else:

            print(
                "Specialization method : "
                "NO USABLE TEXT"
            )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 90)
print("ML QUALITY ANALYSIS SUMMARY")
print("=" * 90)

print()
print("DEGREE")
print("-" * 50)

print(
    f"Rule-based predictions       : "
    f"{degree_rule_count}"
)

print(
    f"ML predictions >= 60%        : "
    f"{degree_ml_count}"
)

print(
    f"ML predictions < 60%         : "
    f"{degree_low_confidence}"
)

if degree_confidences:

    average_degree_confidence = (
        sum(degree_confidences)
        / len(degree_confidences)
    )

    print(
        f"Average ML confidence       : "
        f"{average_degree_confidence:.2f}%"
    )


print()
print("SPECIALIZATION")
print("-" * 50)

print(
    f"Rule-based predictions       : "
    f"{specialization_rule_count}"
)

print(
    f"ML predictions >= 60%        : "
    f"{specialization_ml_count}"
)

print(
    f"ML predictions < 60%         : "
    f"{specialization_low_confidence}"
)

if specialization_confidences:

    average_specialization_confidence = (
        sum(specialization_confidences)
        / len(specialization_confidences)
    )

    print(
        f"Average ML confidence       : "
        f"{average_specialization_confidence:.2f}%"
    )


print()
print("=" * 90)
print("CONFIDENCE THRESHOLD")
print("=" * 90)

print("Current threshold: 60%")

print()
print(
    "This analysis does NOT change the model "
    "or production data."
)

print("=" * 90)
print("ML QUALITY ANALYSIS COMPLETED")
print("=" * 90)