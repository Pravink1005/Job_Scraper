from pathlib import Path
import sys
import csv

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRAINING_FILE = (
    BASE_DIR
    / "ml"
    / "Degree_Prediction_Training_5000_Corrected.csv"
)

PRODUCTION_FILE = (
    BASE_DIR
    / "csv_output"
    / "unified_jobs.csv"
)


# ============================================================
# LOAD TRAINING DATA
# ============================================================

import pandas as pd

training = pd.read_csv(TRAINING_FILE)

training_texts = (
    training["job_description"]
    .fillna("")
    .astype(str)
    .tolist()
)


# ============================================================
# LOAD PRODUCTION DATA
# ============================================================

with open(
    PRODUCTION_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    production = list(csv.DictReader(file))


production_texts = [
    row.get("full_description", "")
    for row in production
]


# ============================================================
# REMOVE EMPTY TEXT
# ============================================================

training_texts = [
    text.strip()
    for text in training_texts
    if text.strip()
]

production_texts = [
    text.strip()
    for text in production_texts
    if text.strip()
]


print("=" * 90)
print("TRAINING vs PRODUCTION TEXT SIMILARITY")
print("=" * 90)

print()
print(
    f"Training descriptions   : "
    f"{len(training_texts)}"
)

print(
    f"Production descriptions : "
    f"{len(production_texts)}"
)


# ============================================================
# TF-IDF
# ============================================================

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=1,
    sublinear_tf=True,
    max_features=20000
)


all_texts = (
    training_texts +
    production_texts
)


matrix = vectorizer.fit_transform(
    all_texts
)


training_matrix = matrix[
    :len(training_texts)
]

production_matrix = matrix[
    len(training_texts):
]


# ============================================================
# PRODUCTION → TRAINING SIMILARITY
# ============================================================

similarities = cosine_similarity(
    production_matrix,
    training_matrix
)


print()
print("=" * 90)
print("PRODUCTION JOB SIMILARITY")
print("=" * 90)


results = []


for index, job in enumerate(production):

    description = (
        job.get("full_description", "")
        .strip()
    )

    if not description:
        continue

    similarity_scores = similarities[index]

    best_score = similarity_scores.max()

    best_training_index = (
        similarity_scores.argmax()
    )

    results.append(
        {
            "job_id": job.get(
                "job_id",
                "Not Specified"
            ),
            "title": job.get(
                "title",
                "Not Specified"
            ),
            "source": job.get(
                "source",
                "Not Specified"
            ),
            "similarity": best_score,
            "training_index":
                best_training_index,
            "training_degree":
                training.iloc[
                    best_training_index
                ]["degree"],
            "training_specialization":
                training.iloc[
                    best_training_index
                ]["specialization"],
        }
    )


# ============================================================
# SORT
# ============================================================

results.sort(
    key=lambda x: x["similarity"]
)


# ============================================================
# LOWEST SIMILARITY
# ============================================================

print()
print("=" * 90)
print("LOWEST SIMILARITY — PRODUCTION JOBS")
print("=" * 90)

for item in results[:10]:

    print()
    print(
        f"Job ID      : "
        f"{item['job_id']}"
    )

    print(
        f"Title       : "
        f"{item['title']}"
    )

    print(
        f"Source      : "
        f"{item['source']}"
    )

    print(
        f"Similarity  : "
        f"{item['similarity']:.4f}"
    )

    print(
        f"Closest degree: "
        f"{item['training_degree']}"
    )

    print(
        f"Closest specialization: "
        f"{item['training_specialization']}"
    )


# ============================================================
# HIGHEST SIMILARITY
# ============================================================

print()
print("=" * 90)
print("HIGHEST SIMILARITY — PRODUCTION JOBS")
print("=" * 90)

for item in results[-10:][::-1]:

    print()
    print(
        f"Job ID      : "
        f"{item['job_id']}"
    )

    print(
        f"Title       : "
        f"{item['title']}"
    )

    print(
        f"Source      : "
        f"{item['source']}"
    )

    print(
        f"Similarity  : "
        f"{item['similarity']:.4f}"
    )

    print(
        f"Closest degree: "
        f"{item['training_degree']}"
    )

    print(
        f"Closest specialization: "
        f"{item['training_specialization']}"
    )


# ============================================================
# SUMMARY
# ============================================================

scores = [
    item["similarity"]
    for item in results
]


if scores:

    import statistics

    print()
    print("=" * 90)
    print("SIMILARITY SUMMARY")
    print("=" * 90)

    print(
        f"Average similarity : "
        f"{statistics.mean(scores):.4f}"
    )

    print(
        f"Median similarity  : "
        f"{statistics.median(scores):.4f}"
    )

    print(
        f"Minimum similarity : "
        f"{min(scores):.4f}"
    )

    print(
        f"Maximum similarity : "
        f"{max(scores):.4f}"
    )

    print()

    very_low = sum(
        score < 0.20
        for score in scores
    )

    low = sum(
        0.20 <= score < 0.40
        for score in scores
    )

    medium = sum(
        0.40 <= score < 0.60
        for score in scores
    )

    high = sum(
        score >= 0.60
        for score in scores
    )

    print(
        f"< 0.20     : {very_low}"
    )

    print(
        f"0.20-0.39  : {low}"
    )

    print(
        f"0.40-0.59  : {medium}"
    )

    print(
        f">= 0.60    : {high}"
    )


print()
print("=" * 90)
print("SIMILARITY ANALYSIS COMPLETED")
print("=" * 90)