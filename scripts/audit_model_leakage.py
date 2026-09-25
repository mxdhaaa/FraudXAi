import pandas as pd
from sklearn.metrics import average_precision_score
from xgboost import XGBClassifier


TRAIN_PATH = "data/processed/splits/train.csv"
VALIDATION_PATH = "data/processed/splits/validation.csv"


TARGET = "isFraud"


ALL_FEATURES = [
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


BALANCE_FEATURES = [
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "origin_balance_error",
    "destination_balance_error",
]


BEHAVIORAL_FEATURES = [
    "sender_tx_count",
    "sender_avg_amount",
    "sender_amount_ratio",
    "time_since_prev_tx",
    "rapid_repeat",
    "receiver_tx_count",
    "receiver_novelty",
    "sender_type_tx_count",
]


def evaluate(feature_set, name):

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    train = pd.read_csv(
        TRAIN_PATH,
        usecols=feature_set + [TARGET]
    )

    validation = pd.read_csv(
        VALIDATION_PATH,
        usecols=feature_set + [TARGET]
    )

    X_train = train[feature_set]
    y_train = train[TARGET].astype(int)

    X_val = validation[feature_set]
    y_val = validation[TARGET].astype(int)

    negative = (y_train == 0).sum()
    positive = (y_train == 1).sum()

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="aucpr",

        n_estimators=200,
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

    probabilities = model.predict_proba(X_val)[:, 1]

    pr_auc = average_precision_score(
        y_val,
        probabilities
    )

    print(f"Features : {len(feature_set)}")
    print(f"PR-AUC   : {pr_auc:.6f}")


print("\nFraudXAi — Leakage / Feature Group Audit")
print("=" * 70)

evaluate(
    ALL_FEATURES,
    "ALL FEATURES"
)

evaluate(
    BALANCE_FEATURES,
    "BALANCE FEATURES ONLY"
)

evaluate(
    BEHAVIORAL_FEATURES,
    "BEHAVIORAL FEATURES ONLY"
)