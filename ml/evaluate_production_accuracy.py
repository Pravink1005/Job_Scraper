from pathlib import Path
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from ml_predictor import predict_job_details


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR.parent

CSV_FILE = PROJECT_ROOT / "csv_output" / "unified_jobs.csv"

LABEL_FILE = BASE_DIR / "production_review_labeled.csv"

DEGREE_ERROR_FILE = BASE_DIR / "production_degree_errors.csv"
SPECIALIZATION_ERROR_FILE = BASE_DIR / "production_specialization_errors.csv"


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value):
    if pd.isna(value):
        return "Not Specified"

    value = str(value).strip()

    if not value:
        return "Not Specified"

    value_lower = value.lower()

    aliases = {
        "not specified": "Not Specified",
        "not_specified": "Not Specified",
        "none": "Not Specified",
        "n/a": "Not Specified",
        "na": "Not Specified",
        "nan": "Not Specified",

        # Degree aliases
        "b.e.": "B.E/B.Tech",
        "b.e": "B.E/B.Tech",
        "b.tech": "B.E/B.Tech",
        "b.tech.": "B.E/B.Tech",

        "m.e.": "M.E/M.Tech",
        "m.e": "M.E/M.Tech",
        "m.tech": "M.E/M.Tech",
        "m.tech.": "M.E/M.Tech",

        "m.sc.": "M.Sc",
        "m.sc": "M.Sc",

        "b.sc.": "B.Sc",
        "b.sc": "B.Sc",

        "b.com.": "B.Com",
        "b.com": "B.Com",

        "bca": "BCA",
        "mca": "MCA",

        "mba": "MBA",
        "bba": "BBA",

        "ph.d": "PhD",
        "ph.d.": "PhD",
        "phd": "PhD",

        "diploma": "Diploma",

        "any bachelor's degree": "Any Bachelor's Degree",
        "any bachelors degree": "Any Bachelor's Degree",

        "any master's degree": "Any Master's Degree",
        "any masters degree": "Any Master's Degree",
    }

    return aliases.get(value_lower, value)


def normalize_specialization(value):
    if pd.isna(value):
        return "Not Specified"

    value = str(value).strip()

    if not value:
        return "Not Specified"

    if value.lower() in {
        "not specified",
        "not_specified",
        "none",
        "n/a",
        "na",
        "nan",
    }:
        return "Not Specified"

    return value


# ============================================================
# LOAD GROUND TRUTH
# ============================================================

def load_ground_truth():
    if not LABEL_FILE.exists():
        raise FileNotFoundError(
            f"Ground-truth file not found:\n{LABEL_FILE}"
        )

    labels = pd.read_csv(LABEL_FILE)

    required_columns = [
        "job_id",
        "actual_degree",
        "actual_specialization",
    ]

    missing = [
        col for col in required_columns
        if col not in labels.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in production_review_labeled.csv: {missing}"
        )

    labels = labels[
        [
            "job_id",
            "actual_degree",
            "actual_specialization",
        ]
    ].copy()

    labels["actual_degree"] = labels["actual_degree"].apply(
        normalize_value
    )

    labels["actual_specialization"] = labels[
        "actual_specialization"
    ].apply(normalize_specialization)

    return labels


# ============================================================
# LOAD CURRENT PRODUCTION JOBS
# ============================================================

def load_production_jobs():
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Production CSV not found:\n{CSV_FILE}"
        )

    df = pd.read_csv(CSV_FILE)

    required_columns = [
        "job_id",
        "title",
        "full_description",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in unified_jobs.csv: {missing}"
        )

    return df


# ============================================================
# CURRENT ML PREDICTIONS
# ============================================================

def generate_current_predictions(df):
    predictions = []

    print("")
    print("=" * 70)
    print("GENERATING CURRENT ML PREDICTIONS")
    print("=" * 70)

    for _, row in df.iterrows():

        description = row.get("full_description", "")

        if pd.isna(description):
            description = ""

        description = str(description)

        result = predict_job_details(description)

        predictions.append(
            {
                "job_id": row["job_id"],
                "title": row.get("title", ""),
                "model_degree": normalize_value(
                    result.get(
                        "predicted_degree",
                        "Not Specified"
                    )
                ),
                "model_specialization": normalize_specialization(
                    result.get(
                        "predicted_specialization",
                        "Not Specified"
                    )
                ),
            }
        )

    return pd.DataFrame(predictions)


# ============================================================
# DEGREE EVALUATION
# ============================================================

def evaluate_degree(df):
    print("")
    print("=" * 70)
    print("DEGREE PRODUCTION EVALUATION")
    print("=" * 70)

    total = len(df)

    correct_mask = (
        df["model_degree"]
        == df["actual_degree"]
    )

    correct = int(correct_mask.sum())
    incorrect = total - correct

    accuracy = (
        correct / total
        if total > 0
        else 0
    )

    specified_mask = (
        df["actual_degree"] != "Not Specified"
    )

    specified_total = int(specified_mask.sum())

    specified_correct = int(
        (
            correct_mask
            & specified_mask
        ).sum()
    )

    print(f"Total jobs                  : {total}")
    print(f"Correct predictions         : {correct}")
    print(f"Incorrect predictions       : {incorrect}")
    print(f"Accuracy                    : {accuracy:.2%}")

    print("")
    print("Ground-truth degree specified:")
    print(
        f"Specified jobs              : {specified_total}"
    )
    print(
        f"Correct among specified    : "
        f"{specified_correct}/{specified_total}"
    )

    errors = df.loc[
        ~correct_mask,
        [
            "job_id",
            "title",
            "model_degree",
            "actual_degree",
        ],
    ].copy()

    print("")
    print("DEGREE MISMATCHES")
    print("-" * 70)

    if errors.empty:
        print("None")
    else:
        print(errors.to_string(index=False))

    errors.to_csv(
        DEGREE_ERROR_FILE,
        index=False
    )

    return accuracy


# ============================================================
# SPECIALIZATION EVALUATION
# ============================================================

def evaluate_specialization(df):
    print("")
    print("=" * 70)
    print("SPECIALIZATION PRODUCTION EVALUATION")
    print("=" * 70)

    total = len(df)

    correct_mask = (
        df["model_specialization"]
        == df["actual_specialization"]
    )

    correct = int(correct_mask.sum())
    incorrect = total - correct

    accuracy = (
        correct / total
        if total > 0
        else 0
    )

    specified_mask = (
        df["actual_specialization"]
        != "Not Specified"
    )

    specified_total = int(
        specified_mask.sum()
    )

    specified_correct = int(
        (
            correct_mask
            & specified_mask
        ).sum()
    )

    print(f"Total jobs                  : {total}")
    print(f"Correct predictions         : {correct}")
    print(f"Incorrect predictions       : {incorrect}")
    print(f"Accuracy                    : {accuracy:.2%}")

    print("")
    print("Ground-truth specialization specified:")
    print(
        f"Specified jobs              : "
        f"{specified_total}"
    )
    print(
        f"Correct among specified    : "
        f"{specified_correct}/{specified_total}"
    )

    errors = df.loc[
        ~correct_mask,
        [
            "job_id",
            "title",
            "model_specialization",
            "actual_specialization",
        ],
    ].copy()

    print("")
    print("SPECIALIZATION MISMATCHES")
    print("-" * 70)

    if errors.empty:
        print("None")
    else:
        print(errors.to_string(index=False))

    errors.to_csv(
        SPECIALIZATION_ERROR_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Classification report
    # --------------------------------------------------------

    print("")
    print("SPECIALIZATION CLASSIFICATION REPORT")
    print("-" * 70)

    labels = sorted(
        set(df["actual_specialization"])
        | set(df["model_specialization"])
    )

    report = classification_report(
        df["actual_specialization"],
        df["model_specialization"],
        labels=labels,
        zero_division=0,
    )

    print(report)

    return accuracy


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("CURRENT PRODUCTION ML ACCURACY EVALUATION")
    print("=" * 70)

    print("")
    print(f"Production CSV : {CSV_FILE}")
    print(f"Ground truth   : {LABEL_FILE}")

    production = load_production_jobs()
    ground_truth = load_ground_truth()

    print("")
    print(
        f"Production jobs loaded: {len(production)}"
    )

    print(
        f"Ground-truth jobs loaded: {len(ground_truth)}"
    )

    # --------------------------------------------------------
    # Generate CURRENT predictions
    # --------------------------------------------------------

    predictions = generate_current_predictions(
        production
    )

    # --------------------------------------------------------
    # Join current predictions with ground truth
    # --------------------------------------------------------

    evaluation = predictions.merge(
        ground_truth,
        on="job_id",
        how="inner",
    )

    print("")
    print(
        f"Jobs available for evaluation: "
        f"{len(evaluation)}"
    )

    if len(evaluation) == 0:
        raise RuntimeError(
            "No matching job_id values between "
            "production CSV and ground-truth file."
        )

    # --------------------------------------------------------
    # Degree
    # --------------------------------------------------------

    degree_accuracy = evaluate_degree(
        evaluation
    )

    # --------------------------------------------------------
    # Specialization
    # --------------------------------------------------------

    specialization_accuracy = evaluate_specialization(
        evaluation
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("")
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(
        f"Degree Accuracy           : "
        f"{degree_accuracy:.2%}"
    )

    print(
        f"Specialization Accuracy   : "
        f"{specialization_accuracy:.2%}"
    )

    print("")
    print("Updated error files:")
    print(
        f"Degree          : {DEGREE_ERROR_FILE}"
    )
    print(
        f"Specialization  : "
        f"{SPECIALIZATION_ERROR_FILE}"
    )

    print("")
    print("=" * 70)
    print("CURRENT ML EVALUATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()