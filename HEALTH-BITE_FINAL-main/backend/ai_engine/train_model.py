import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Paths
BASE_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(BASE_DIR, "training_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "food_recommender.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "label_encoders.pkl")

def train_model():
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        return

    # 1. Load dataset
    df = pd.read_csv(DATASET_PATH)

    # 2. Preprocess data
    categorical_cols = ["bmi_category", "gender", "activity_level", "diet_type", "goal", "health_condition"]
    target_col = "recommended_food"

    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    # Encode target
    target_le = LabelEncoder()
    df[target_col] = target_le.fit_transform(df[target_col])
    encoders[target_col] = target_le

    # Split features and target
    X = df.drop(target_col, axis=1)
    y = df[target_col]

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Train candidate models
    models = {}

    # RandomForest
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    models["RandomForest"] = {
        "model": rf_model,
        "accuracy": accuracy_score(y_test, rf_preds),
        "f1": f1_score(y_test, rf_preds, average="weighted", zero_division=0),
        "precision": precision_score(y_test, rf_preds, average="weighted", zero_division=0),
        "recall": recall_score(y_test, rf_preds, average="weighted", zero_division=0),
    }

    # Naive Bayes
    nb_model = GaussianNB()
    nb_model.fit(X_train, y_train)
    nb_preds = nb_model.predict(X_test)
    models["GaussianNB"] = {
        "model": nb_model,
        "accuracy": accuracy_score(y_test, nb_preds),
        "f1": f1_score(y_test, nb_preds, average="weighted", zero_division=0),
        "precision": precision_score(y_test, nb_preds, average="weighted", zero_division=0),
        "recall": recall_score(y_test, nb_preds, average="weighted", zero_division=0),
    }

    # Decision Tree
    dt_model = DecisionTreeClassifier(max_depth=18, min_samples_split=8, random_state=42)
    dt_model.fit(X_train, y_train)
    dt_preds = dt_model.predict(X_test)
    models["DecisionTree"] = {
        "model": dt_model,
        "accuracy": accuracy_score(y_test, dt_preds),
        "f1": f1_score(y_test, dt_preds, average="weighted", zero_division=0),
        "precision": precision_score(y_test, dt_preds, average="weighted", zero_division=0),
        "recall": recall_score(y_test, dt_preds, average="weighted", zero_division=0),
    }

    for name, stats in models.items():
        print(f"{name} Accuracy: {stats['accuracy']:.4f} | F1: {stats['f1']:.4f}")

    # 4. Save best model by weighted F1 then accuracy
    best_name, best_stats = max(
        models.items(),
        key=lambda item: (item[1]["f1"], item[1]["accuracy"])
    )
    best_model = best_stats["model"]
    print(f"Saving {best_name} as the best model.")

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(encoders, ENCODER_PATH)
    print(f"Model saved to {MODEL_PATH}")
    print(f"Encoders saved to {ENCODER_PATH}")
    
    candidate_summary = []
    for name, stats in models.items():
        candidate_summary.append(f"{name} 🎯 {stats['accuracy']:.4f} | F1: {stats['f1']:.4f}")

    return {
        "model_name": best_name,
        "accuracy": best_stats["accuracy"],
        "f1": best_stats["f1"],
        "precision": best_stats["precision"],
        "recall": best_stats["recall"],
        "candidates": " || ".join(candidate_summary)
    }

if __name__ == "__main__":
    train_model()
