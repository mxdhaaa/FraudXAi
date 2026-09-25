from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    confusion_matrix,
)


SPLIT_DIR = Path("data/processed/splits")


def evaluate(
    name: str,
    df: pd.DataFrame,
    threshold: float,
):
    y_true = df["isFraud"].to_numpy()

    y_score = (
        df["amount"].to_numpy() >= threshold
    ).astype(int)

    precision = precision_score(
        y_true,
        y_score,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_score,
        zero_division=0,
    )

    pr_auc = average_precision_score(
        y_true,
        y_score,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_score,
        labels=[0, 1],
    ).ravel()

    flagged_rate = (
        y_score.mean() * 100
    )

    print(f"\n{name}")
    print("-" * 50)
    print(f"Transactions : {len(df):,}")
    print(f"Fraud        : {y_true.sum():,}")
    print(f"Threshold    : {threshold:,.2f}")
    print(f"Flagged      : {y_score.sum():,}")
    print(f"Flagged rate : {flagged_rate:.4f}%")
    print(f"PR-AUC       : {pr_auc:.6f}")
    print(f"Precision    : {precision:.6f}")
    print(f"Recall       : {recall:.6f}")
    print(f"TN           : {tn:,}")
    print(f"FP           : {fp:,}")
    print(f"FN           : {fn:,}")
    print(f"TP           : {tp:,}")


def main():

    print("=" * 70)
    print("FraudXAi — Rule-Based Baseline")
    print("=" * 70)

    train = pd.read_csv(
        SPLIT_DIR / "train.csv"
    )

    validation = pd.read_csv(
        SPLIT_DIR / "validation.csv"
    )

    test = pd.read_csv(
        SPLIT_DIR / "test.csv"
    )

    # ---------------------------------------------------------
    # Select threshold ONLY from training data.
    #
    # We use the 99.9th percentile of legitimate transaction
    # amounts as a simple, reproducible rule.
    # ---------------------------------------------------------

    legitimate_train = train.loc[
        train["isFraud"] == 0,
        "amount",
    ]

    threshold = float(
        np.percentile(
            legitimate_train,
            99.9,
        )
    )

    print(
        f"\nBaseline threshold selected "
        f"from training data: {threshold:,.2f}"
    )

    evaluate(
        "TRAIN",
        train,
        threshold,
    )

    evaluate(
        "VALIDATION",
        validation,
        threshold,
    )

    evaluate(
        "TEST",
        test,
        threshold,
    )


if __name__ == "__main__":
    main()