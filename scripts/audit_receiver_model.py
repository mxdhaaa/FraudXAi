import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import average_precision_score


TRAIN_PATH = "data/processed/splits/train.csv"
VALIDATION_PATH = "data/processed/splits/validation.csv"


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
print("FraudXAi — Receiver Behavioral Model Audit")
print("=" * 70)

X_train, y_train = load(TRAIN_PATH)
X_val, y_val = load(VALIDATION_PATH)

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

print("\nTraining receiver-focused model...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False,
)

probabilities = model.predict_proba(X_val)[:, 1]

pr_auc = average_precision_score(
    y_val,
    probabilities
)

print("\nVALIDATION")
print("-" * 50)
print(f"PR-AUC: {pr_auc:.6f}")

print("\nFeature importance")
print("-" * 50)

for feature, importance in sorted(
    zip(FEATURES, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True,
):
    print(f"{feature:30s} {importance:.6f}")