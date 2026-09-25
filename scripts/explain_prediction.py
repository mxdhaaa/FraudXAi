import json
import os

import pandas as pd
import shap
from xgboost import XGBClassifier


TRAIN_PATH = "data/processed/splits/train.csv"
TEST_PATH = "data/processed/splits/test.csv"

MODEL_DIR = "ml/models"
MODEL_PATH = os.path.join(
    MODEL_DIR,
    "receiver_behavioral_xgboost.json"
)

FEATURES = [
    "amount",
    "log_amount",
    "type_code",
    "hour",
    "day",
    "step",
    "receiver_tx_count",
    "receiver_novelty",
]


def main():

    print("=" * 70)
    print("FraudXAi — Individual Prediction Explanation")
    print("=" * 70)

    # --------------------------------------------------------
    # Load training data
    # --------------------------------------------------------

    print("\nLoading training data...")

    train = pd.read_csv(
        TRAIN_PATH,
        usecols=FEATURES + ["isFraud"]
    )

    X_train = train[FEATURES]
    y_train = train["isFraud"].astype(int)

    # --------------------------------------------------------
    # Train receiver-focused model
    # --------------------------------------------------------

    negative = (y_train == 0).sum()
    positive = (y_train == 1).sum()

    print("Training receiver-focused model...")

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="aucpr",

        n_estimators=300,
        max_depth=5,
        learning_rate=0.08,

        subsample=0.8,
        colsample_bytree=0.8,

        min_child_weight=5,

        scale_pos_weight=negative / positive,

        tree_method="hist",
        n_jobs=-1,

        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        verbose=False
    )

    # --------------------------------------------------------
    # Save the correct model
    # --------------------------------------------------------

    model.save_model(MODEL_PATH)

    print("\nReceiver model saved:")
    print(MODEL_PATH)

    # --------------------------------------------------------
    # Load one fraud example from test data
    # --------------------------------------------------------

    print("\nLoading test transaction...")

    df = pd.read_csv(
        TEST_PATH,
        usecols=FEATURES + ["isFraud"]
    )

    fraud_rows = df[df["isFraud"] == 1]

    if fraud_rows.empty:
        raise RuntimeError(
            "No fraud transaction found in test set."
        )

    sample = fraud_rows.iloc[[0]]

    X_sample = sample[FEATURES]

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    probability = float(
        model.predict_proba(X_sample)[0, 1]
    )

    print("\nTransaction")
    print("-" * 50)

    for feature in FEATURES:
        print(
            f"{feature:25s}: "
            f"{sample.iloc[0][feature]}"
        )

    print("\nActual label      : FRAUD")
    print(
        f"Fraud probability : "
        f"{probability:.6f}"
    )

    # --------------------------------------------------------
    # SHAP explanation
    # --------------------------------------------------------

    print("\nCalculating SHAP explanation...")

    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(
        X_sample
    )

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    shap_values = shap_values[0]

    explanation = sorted(
        zip(
            FEATURES,
            X_sample.iloc[0].values,
            shap_values
        ),
        key=lambda x: abs(x[2]),
        reverse=True
    )

    print("\nSHAP Feature Contributions")
    print("-" * 75)

    print(
        f"{'Feature':30s}"
        f"{'Value':18s}"
        f"{'SHAP contribution':20s}"
    )

    print("-" * 75)

    for feature, value, contribution in explanation:

        direction = (
            "increases risk"
            if contribution > 0
            else "decreases risk"
        )

        print(
            f"{feature:30s}"
            f"{str(value):18s}"
            f"{contribution: .6f}  "
            f"({direction})"
        )

    # --------------------------------------------------------
    # Save explanation
    # --------------------------------------------------------

    output = {
        "actual_label": int(
            sample.iloc[0]["isFraud"]
        ),
        "fraud_probability": probability,
        "features": [
            {
                "feature": feature,
                "value": float(value),
                "shap_contribution": float(
                    contribution
                ),
                "direction": (
                    "increases_risk"
                    if contribution > 0
                    else "decreases_risk"
                ),
            }
            for feature, value, contribution in explanation
        ],
    }

    output_path = os.path.join(
        MODEL_DIR,
        "sample_prediction_explanation.json"
    )

    with open(output_path, "w") as f:
        json.dump(
            output,
            f,
            indent=2
        )

    print("\nExplanation saved:")
    print(output_path)

    print("\nExplanation complete.")


if __name__ == "__main__":
    main()