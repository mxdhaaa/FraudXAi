import os
import json
import joblib
import numpy as np
import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import average_precision_score, precision_score, recall_score


# ============================================================
# FraudXAi — XGBoost Fraud Detection Model
# ============================================================

TRAIN_PATH = "data/processed/splits/train.csv"
VALIDATION_PATH = "data/processed/splits/validation.csv"

MODEL_DIR = "ml/models"
MODEL_PATH = os.path.join(MODEL_DIR, "fraud_xgboost.json")
FEATURE_PATH = os.path.join(MODEL_DIR, "fraud_xgboost_features.json")


TARGET = "isFraud"

FEATURES = [
    "step",
    "hour",
    "day",
    "amount",
    "log_amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "origin_balance_error",
    "destination_balance_error",
    "type_code",
    "sender_tx_count",
    "sender_avg_amount",
    "sender_amount_ratio",
    "time_since_prev_tx",
    "rapid_repeat",
    "receiver_tx_count",
    "receiver_novelty",
    "sender_type_tx_count",
]


def load_data(path):
    print(f"\nLoading: {path}")

    df = pd.read_csv(path, usecols=FEATURES + [TARGET])

    X = df[FEATURES]
    y = df[TARGET].astype(int)

    print(f"Rows      : {len(df):,}")
    print(f"Fraud     : {y.sum():,}")
    print(f"Legitimate: {(y == 0).sum():,}")
    print(f"Fraud rate: {y.mean() * 100:.4f}%")

    return X, y


def main():

    print("=" * 70)
    print("FraudXAi — XGBoost Fraud Detection")
    print("=" * 70)

    os.makedirs(MODEL_DIR, exist_ok=True)

    # --------------------------------------------------------
    # Load chronological training and validation data
    # --------------------------------------------------------

    X_train, y_train = load_data(TRAIN_PATH)
    X_val, y_val = load_data(VALIDATION_PATH)

    # --------------------------------------------------------
    # Class imbalance
    # --------------------------------------------------------

    negative = int((y_train == 0).sum())
    positive = int((y_train == 1).sum())

    scale_pos_weight = negative / positive

    print("\nClass imbalance")
    print("-" * 50)
    print(f"Negative class : {negative:,}")
    print(f"Positive class : {positive:,}")
    print(f"Scale pos weight: {scale_pos_weight:.2f}")

    # --------------------------------------------------------
    # XGBoost model
    # --------------------------------------------------------

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="aucpr",

        n_estimators=500,
        max_depth=6,
        learning_rate=0.08,

        subsample=0.8,
        colsample_bytree=0.8,

        min_child_weight=5,
        gamma=0.1,

        reg_alpha=0.1,
        reg_lambda=1.0,

        scale_pos_weight=scale_pos_weight,

        tree_method="hist",
        n_jobs=-1,

        random_state=42,
    )

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    print("\nTraining XGBoost...")
    print("This may take some time because the dataset is large.")

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    # --------------------------------------------------------
    # Validation predictions
    # --------------------------------------------------------

    print("\nGenerating validation predictions...")

    val_prob = model.predict_proba(X_val)[:, 1]

    pr_auc = average_precision_score(y_val, val_prob)

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    print(f"PR-AUC: {pr_auc:.6f}")

    # --------------------------------------------------------
    # Find threshold based on F1
    # --------------------------------------------------------

    print("\nSearching for validation threshold...")

    thresholds = np.linspace(0.01, 0.99, 99)

    best_threshold = 0.5
    best_f1 = -1

    for threshold in thresholds:

        predictions = (val_prob >= threshold).astype(int)

        precision = precision_score(
            y_val,
            predictions,
            zero_division=0
        )

        recall = recall_score(
            y_val,
            predictions,
            zero_division=0
        )

        if precision + recall == 0:
            f1 = 0
        else:
            f1 = 2 * precision * recall / (precision + recall)

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    print(f"Best threshold: {best_threshold:.2f}")
    print(f"Best F1       : {best_f1:.6f}")

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    model.save_model(MODEL_PATH)

    metadata = {
        "features": FEATURES,
        "validation_pr_auc": float(pr_auc),
        "validation_best_threshold": float(best_threshold),
        "validation_best_f1": float(best_f1),
        "scale_pos_weight": float(scale_pos_weight),
        "random_state": 42,
    }

    with open(FEATURE_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print("\nModel saved:")
    print(MODEL_PATH)

    print("\nFeature metadata saved:")
    print(FEATURE_PATH)

    print("\nTraining complete.")


if __name__ == "__main__":
    main()Get-Content backend/app/api.py