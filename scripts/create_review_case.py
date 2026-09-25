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

OUTPUT_PATH = os.path.join(
    MODEL_DIR,
    "review_case.json"
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


TYPE_NAMES = {
    0: "CASH_IN",
    1: "CASH_OUT",
    2: "DEBIT",
    3: "PAYMENT",
    4: "TRANSFER",
}


REVIEW_THRESHOLD = 0.60
BLOCK_THRESHOLD = 0.95


def train_model():

    train = pd.read_csv(
        TRAIN_PATH,
        usecols=FEATURES + ["isFraud"]
    )

    X_train = train[FEATURES]
    y_train = train["isFraud"].astype(int)

    negative = (y_train == 0).sum()
    positive = (y_train == 1).sum()

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

    model.save_model(MODEL_PATH)

    return model


def get_decision(probability):

    if probability >= BLOCK_THRESHOLD:
        return "BLOCK"

    if probability >= REVIEW_THRESHOLD:
        return "REVIEW"

    return "APPROVE"


def main():

    print("=" * 70)
    print("FraudXAi — Human-in-the-Loop Review Case")
    print("=" * 70)

    # --------------------------------------------------------
    # Load / train model
    # --------------------------------------------------------

    print("\nLoading receiver behavioral model...")

    if os.path.exists(MODEL_PATH):

        model = XGBClassifier()
        model.load_model(MODEL_PATH)

    else:

        print("Model not found. Training model...")
        model = train_model()

    # --------------------------------------------------------
    # Load test data
    # --------------------------------------------------------

    print("Loading test transactions...")

    df = pd.read_csv(
        TEST_PATH,
        usecols=FEATURES + ["isFraud"]
    )

    # --------------------------------------------------------
    # Find a transaction that falls into REVIEW
    # --------------------------------------------------------

    probabilities = model.predict_proba(
        df[FEATURES]
    )[:, 1]

    df["risk_probability"] = probabilities

    review_rows = df[
        (df["risk_probability"] >= REVIEW_THRESHOLD)
        & (df["risk_probability"] < BLOCK_THRESHOLD)
    ]

    if review_rows.empty:
        raise RuntimeError(
            "No REVIEW transactions found."
        )

    sample = review_rows.iloc[[0]]

    X_sample = sample[FEATURES]

    probability = float(
        sample.iloc[0]["risk_probability"]
    )

    decision = get_decision(probability)

    # --------------------------------------------------------
    # SHAP explanation
    # --------------------------------------------------------

    print("Generating SHAP explanation...")

    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(
        X_sample
    )

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    shap_values = shap_values[0]

    explanations = []

    for feature, value, contribution in sorted(
        zip(
            FEATURES,
            X_sample.iloc[0].values,
            shap_values
        ),
        key=lambda x: abs(x[2]),
        reverse=True
    ):

        explanations.append({
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
        })

    # --------------------------------------------------------
    # Behavioral evidence
    # --------------------------------------------------------

    row = sample.iloc[0]

    evidence = []

    if row["receiver_novelty"] == 1:
        evidence.append(
            "Receiver has no prior transaction history "
            "in the observed history."
        )

    if row["receiver_tx_count"] == 0:
        evidence.append(
            "Receiver transaction count before this "
            "transaction is zero."
        )

    if int(row["type_code"]) in [1, 4]:
        evidence.append(
            f"Transaction type is "
            f"{TYPE_NAMES[int(row['type_code'])]}, "
            f"a transaction type containing fraud cases "
            f"in the PaySim dataset."
        )

    # --------------------------------------------------------
    # Agent recommendation
    # --------------------------------------------------------

    recommendation = (
        "Send to human investigator for manual review. "
        "The model identifies elevated fraud risk, but "
        "the model recommendation is not the final decision."
    )

    # --------------------------------------------------------
    # Review case
    # --------------------------------------------------------

    case = {
        "case_type": "FRAUD_REVIEW",

        "transaction": {
            "amount": float(row["amount"]),
            "transaction_type": TYPE_NAMES[
                int(row["type_code"])
            ],
            "step": int(row["step"]),
            "hour": int(row["hour"]),
            "day": int(row["day"]),
        },

        "risk": {
            "fraud_probability": probability,
            "decision": decision,
            "review_threshold": REVIEW_THRESHOLD,
            "block_threshold": BLOCK_THRESHOLD,
        },

        "behavioral_evidence": evidence,

        "shap_explanation": explanations,

        "agent": {
            "recommendation": recommendation,
            "final_decision_authority": "HUMAN_INVESTIGATOR",
        },

        "human_review_options": [
            "CONFIRM_FRAUD",
            "CONFIRM_LEGITIMATE",
            "ESCALATE",
        ],
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(OUTPUT_PATH, "w") as f:
        json.dump(
            case,
            f,
            indent=2
        )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("REVIEW CASE")
    print("=" * 70)

    print(
        f"Transaction type : "
        f"{case['transaction']['transaction_type']}"
    )

    print(
        f"Amount           : "
        f"{case['transaction']['amount']:,.2f}"
    )

    print(
        f"Fraud probability: "
        f"{probability:.6f}"
    )

    print(
        f"System decision  : "
        f"{decision}"
    )

    print("\nBehavioral evidence")
    print("-" * 50)

    for item in evidence:
        print(f"- {item}")

    print("\nTop SHAP factors")
    print("-" * 50)

    for item in explanations[:5]:

        direction = (
            "↑"
            if item["shap_contribution"] > 0
            else "↓"
        )

        print(
            f"{direction} "
            f"{item['feature']}: "
            f"{item['shap_contribution']:.6f}"
        )

    print("\nAgent recommendation")
    print("-" * 50)
    print(recommendation)

    print("\nHuman decision options")
    print("-" * 50)

    for option in case["human_review_options"]:
        print(f"- {option}")

    print("\nReview case saved:")
    print(OUTPUT_PATH)

    print("\nComplete.")


if __name__ == "__main__":
    main()