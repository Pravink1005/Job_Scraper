from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from ml_predictor import extract_degree_text, extract_specialization_text


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Degree_Prediction_Training_5000_Corrected.csv"
MODEL_DIR = BASE_DIR / "models"


def prepare_texts(descriptions, extractor):
    prepared = []
    for description in descriptions:
        extracted = extractor(description)
        prepared.append(extracted.strip() or description)
    return prepared


def train_one_model(texts, labels, name):
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    train_vectors = vectorizer.fit_transform(train_texts)
    test_vectors = vectorizer.transform(test_texts)

    model = LogisticRegression(max_iter=2000, class_weight="balanced")
    model.fit(train_vectors, train_labels)
    predictions = model.predict(test_vectors)

    accuracy = accuracy_score(test_labels, predictions)
    print(f"{name} validation accuracy: {accuracy:.2%}")
    return vectorizer, model


def main():
    data = pd.read_csv(DATA_FILE)
    required_columns = {"job_description", "degree", "specialization"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    descriptions = data["job_description"].fillna("").astype(str).tolist()
    degree_labels = data["degree"].astype(str).tolist()
    specialization_labels = data["specialization"].astype(str).tolist()

    degree_texts = prepare_texts(descriptions, extract_degree_text)
    specialization_texts = prepare_texts(descriptions, extract_specialization_text)

    degree_vectorizer, degree_model = train_one_model(
        degree_texts, degree_labels, "Degree model"
    )
    specialization_vectorizer, specialization_model = train_one_model(
        specialization_texts, specialization_labels, "Specialization model"
    )

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(degree_vectorizer, MODEL_DIR / "degree_vectorizer.pkl")
    joblib.dump(degree_model, MODEL_DIR / "degree_model.pkl")
    joblib.dump(specialization_vectorizer, MODEL_DIR / "specialization_vectorizer.pkl")
    joblib.dump(specialization_model, MODEL_DIR / "specialization_model.pkl")
    print(f"Saved aligned models to {MODEL_DIR}")


if __name__ == "__main__":
    main()
