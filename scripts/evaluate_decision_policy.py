import pandas as pd
import numpy as np

from xgboost import XGBClassifier
from sklearn.metrics import confusion_matrix


TRAIN_PATH = "data/processed/splits/train.csv"
VALIDATION_PATH = "data/processed/splits/validation.csv"
TEST_PATH = "data/processed/splits/test.csv"


TARGET = "isFraud"

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


def load(path):
    df = pd.read_csv(path, usecols=FEATURES + [TARGET])
    return df[FEATURES], df[TARGET].astype(int)


def train_model(X_train, y_train, X_val, y_val):

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
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    return model


def evaluate_policy(y_true, probabilities, review_threshold, block_threshold):

    decisions = np.where(
        probabilities >= block_threshold,
        "BLOCK",
        np.where(
            probabilities >= review_threshold,
            "REVIEW",
            "APPROVE"
        )
    )

    approve = decisions == "APPROVE"
    review = decisions == "REVIEW"
    block = decisions == "BLOCK"

    fraud = y_true.to_numpy() == 1
    legitimate = ~fraud

    # Fraud outcomes
    fraud_approved = int((approve & fraud).sum())
    fraud_reviewed = int((review & fraud).sum())
    fraud_blocked = int((block & fraud).sum())

    # Legitimate outcomes
    legit_approved = int((approve & legitimate).sum())
    legit_reviewed = int((review & legitimate).sum())
    legit_blocked = int((block & legitimate).sum())

    total = len(y_true)
    total_fraud = int(fraud.sum())

    return {
        "approve": int(approve.sum()),
        "review": int(review.sum()),
        "block": int(block.sum()),

        "fraud_approved": fraud_approved,
        "fraud_reviewed": fraud_reviewed,
        "fraud_blocked": fraud_blocked,

        "legit_approved": legit_approved,
        "legit_reviewed": legit_reviewed,
        "legit_blocked": legit_blocked,

        "fraud_capture_rate": (
            (fraud_reviewed + fraud_blocked) / total_fraud
            if total_fraud else 0
        ),

        "review_rate": review.sum() / total,
        "block_rate": block.sum() / total,
    }


print("=" * 70)
print("FraudXAi — Cost-Aware Decision Policy")
print("=" * 70)


# ============================================================
# Load data
# ============================================================

X_train, y_train = load(TRAIN_PATH)
X_val, y_val = load(VALIDATION_PATH)
X_test, y_test = load(TEST_PATH)


print("\nTraining model...")

model = train_model(
    X_train,
    y_train,
    X_val,
    y_val
)


# ============================================================
# Generate probabilities
# ============================================================

val_prob = model.predict_proba(X_val)[:, 1]
test_prob = model.predict_proba(X_test)[:, 1]


# ============================================================
# Business assumptions
# ============================================================
#
# These are EXPLICIT experimental assumptions, not real
# financial estimates.
#
# We will vary them later for sensitivity analysis.
#
# FN_COST:
#   Expected cost of allowing a fraudulent transaction through.
#
# FP_COST:
#   Operational/customer cost of blocking a legitimate
#   transaction.
#
# REVIEW_COST:
#   Cost of sending a transaction to a human investigator.
#
# ============================================================

FN_COST = 1000.0
FP_COST = 25.0
REVIEW_COST = 5.0


print("\nExperimental cost assumptions")
print("-" * 50)
print(f"Fraud approved cost : {FN_COST:.2f}")
print(f"False block cost    : {FP_COST:.2f}")
print(f"Manual review cost  : {REVIEW_COST:.2f}")


# ============================================================
# Select policy on VALIDATION ONLY
# ============================================================

print("\nSearching validation decision policy...")

candidate_review_thresholds = np.arange(
    0.10,
    0.91,
    0.05
)

candidate_block_thresholds = np.arange(
    0.50,
    1.00,
    0.05
)


best_policy = None
best_cost = float("inf")


for review_threshold in candidate_review_thresholds:

    for block_threshold in candidate_block_thresholds:

        if block_threshold <= review_threshold:
            continue

        result = evaluate_policy(
            y_val,
            val_prob,
            review_threshold,
            block_threshold
        )

        expected_cost = (
            result["fraud_approved"] * FN_COST
            + result["legit_blocked"] * FP_COST
            + result["review"] * REVIEW_COST
        )

        if expected_cost < best_cost:

            best_cost = expected_cost

            best_policy = {
                "review_threshold": float(review_threshold),
                "block_threshold": float(block_threshold),
                "validation_cost": float(expected_cost),
                **result,
            }


# ============================================================
# Validation policy
# ============================================================

print("\n" + "=" * 70)
print("SELECTED VALIDATION POLICY")
print("=" * 70)

print(
    f"APPROVE  : probability < "
    f"{best_policy['review_threshold']:.2f}"
)

print(
    f"REVIEW   : "
    f"{best_policy['review_threshold']:.2f} <= probability < "
    f"{best_policy['block_threshold']:.2f}"
)

print(
    f"BLOCK    : probability >= "
    f"{best_policy['block_threshold']:.2f}"
)

print(f"\nValidation expected cost: {best_policy['validation_cost']:,.2f}")

print("\nValidation decisions")
print("-" * 50)
print(f"APPROVE : {best_policy['approve']:,}")
print(f"REVIEW  : {best_policy['review']:,}")
print(f"BLOCK   : {best_policy['block']:,}")

print(
    f"\nFraud captured: "
    f"{best_policy['fraud_capture_rate'] * 100:.2f}%"
)


# ============================================================
# Frozen TEST evaluation
# ============================================================

test_result = evaluate_policy(
    y_test,
    test_prob,
    best_policy["review_threshold"],
    best_policy["block_threshold"]
)


test_cost = (
    test_result["fraud_approved"] * FN_COST
    + test_result["legit_blocked"] * FP_COST
    + test_result["review"] * REVIEW_COST
)


print("\n" + "=" * 70)
print("FROZEN TEST DECISION POLICY")
print("=" * 70)

print(
    f"APPROVE  : probability < "
    f"{best_policy['review_threshold']:.2f}"
)

print(
    f"REVIEW   : "
    f"{best_policy['review_threshold']:.2f} <= probability < "
    f"{best_policy['block_threshold']:.2f}"
)

print(
    f"BLOCK    : probability >= "
    f"{best_policy['block_threshold']:.2f}"
)

print(f"\nTest expected cost: {test_cost:,.2f}")

print("\nTest decisions")
print("-" * 50)
print(f"APPROVE : {test_result['approve']:,}")
print(f"REVIEW  : {test_result['review']:,}")
print(f"BLOCK   : {test_result['block']:,}")

print("\nFraud outcomes")
print("-" * 50)
print(f"Fraud approved : {test_result['fraud_approved']:,}")
print(f"Fraud reviewed : {test_result['fraud_reviewed']:,}")
print(f"Fraud blocked  : {test_result['fraud_blocked']:,}")

print("\nLegitimate outcomes")
print("-" * 50)
print(f"Legit approved : {test_result['legit_approved']:,}")
print(f"Legit reviewed : {test_result['legit_reviewed']:,}")
print(f"Legit blocked  : {test_result['legit_blocked']:,}")

print(
    f"\nFraud captured: "
    f"{test_result['fraud_capture_rate'] * 100:.2f}%"
)

print(
    f"Review rate: "
    f"{test_result['review_rate'] * 100:.4f}%"
)

print(
    f"Block rate: "
    f"{test_result['block_rate'] * 100:.4f}%"
)

print("\nEvaluation complete.")