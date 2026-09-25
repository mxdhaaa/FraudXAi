import pandas as pd
import numpy as np

from xgboost import XGBClassifier
from sklearn.metrics import average_precision_score


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


print("=" * 70)
print("FraudXAi — Fixed Review Budget Evaluation")
print("=" * 70)


# ============================================================
# Load data
# ============================================================

X_train, y_train = load(TRAIN_PATH)
X_val, y_val = load(VALIDATION_PATH)
X_test, y_test = load(TEST_PATH)


# ============================================================
# Train model
# ============================================================

negative = (y_train == 0).sum()
positive = (y_train == 1).sum()

scale_pos_weight = negative / positive

model = XGBClassifier(
    objective="binary:logistic",
    eval_metric="aucpr",

    n_estimators=300,
    max_depth=5,
    learning_rate=0.08,

    subsample=0.8,
    colsample_bytree=0.8,

    min_child_weight=5,

    scale_pos_weight=scale_pos_weight,

    tree_method="hist",
    n_jobs=-1,

    random_state=42,
)

print("\nTraining model...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False,
)


# ============================================================
# Validation PR-AUC
# ============================================================

val_prob = model.predict_proba(X_val)[:, 1]

val_pr_auc = average_precision_score(
    y_val,
    val_prob
)

print(f"\nValidation PR-AUC: {val_pr_auc:.6f}")


# ============================================================
# Frozen test predictions
# ============================================================

print("Generating test predictions...")

test_prob = model.predict_proba(X_test)[:, 1]

test_pr_auc = average_precision_score(
    y_test,
    test_prob
)

print(f"Test PR-AUC: {test_pr_auc:.6f}")


# ============================================================
# Fixed review budgets
# ============================================================

budgets = [
    0.001,   # 0.1%
    0.0025,  # 0.25%
    0.005,   # 0.5%
    0.01,    # 1%
]


results = []

order = np.argsort(-test_prob)

sorted_labels = y_test.iloc[order].to_numpy()
sorted_prob = test_prob[order]

total_fraud = int(y_test.sum())
total_transactions = len(y_test)


for budget in budgets:

    review_count = max(
        1,
        int(total_transactions * budget)
    )

    reviewed_labels = sorted_labels[:review_count]
    reviewed_scores = sorted_prob[:review_count]

    true_positives = int(reviewed_labels.sum())

    precision = true_positives / review_count

    recall = (
        true_positives / total_fraud
        if total_fraud > 0
        else 0
    )

    threshold = float(reviewed_scores[-1])

    results.append({
        "budget": budget,
        "review_count": review_count,
        "threshold": threshold,
        "fraud_found": true_positives,
        "precision": precision,
        "recall": recall,
    })


# ============================================================
# Results
# ============================================================

print("\n" + "=" * 70)
print("FIXED REVIEW BUDGET RESULTS")
print("=" * 70)

print(
    f"{'Budget':<10}"
    f"{'Reviews':<12}"
    f"{'Threshold':<14}"
    f"{'Fraud Found':<14}"
    f"{'Precision':<14}"
    f"{'Recall':<14}"
)

print("-" * 70)

for result in results:

    print(
        f"{result['budget'] * 100:<9.2f}%"
        f"{result['review_count']:<12,}"
        f"{result['threshold']:<14.6f}"
        f"{result['fraud_found']:<14,}"
        f"{result['precision']:<14.4f}"
        f"{result['recall']:<14.4f}"
    )


print("\nTotal test transactions:", f"{total_transactions:,}")
print("Total test fraud:", f"{total_fraud:,}")

print("\nEvaluation complete.")