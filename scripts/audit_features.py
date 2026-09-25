from pathlib import Path

import pandas as pd


FEATURE_PATH = Path(
    "data/processed/fraud_features.csv"
)


def main():
    if not FEATURE_PATH.exists():
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_PATH}"
        )

    df = pd.read_csv(FEATURE_PATH)

    print("=" * 70)
    print("FraudXAi — Behavioral Feature Audit")
    print("=" * 70)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    # ---------------------------------------------------------
    # 1. Missing values
    # ---------------------------------------------------------

    missing = df.isna().sum()

    print("\nMissing values:")

    print(
        missing[missing > 0]
        if missing.any()
        else "None"
    )

    # ---------------------------------------------------------
    # 2. Sender count sanity
    # ---------------------------------------------------------

    invalid_sender_counts = (
        df["sender_tx_count"] < 0
    ).sum()

    print(
        f"\nInvalid sender counts: "
        f"{invalid_sender_counts}"
    )

    # ---------------------------------------------------------
    # 3. Receiver count sanity
    # ---------------------------------------------------------

    invalid_receiver_counts = (
        df["receiver_tx_count"] < 0
    ).sum()

    print(
        f"Invalid receiver counts: "
        f"{invalid_receiver_counts}"
    )

    # ---------------------------------------------------------
    # 4. First transaction behavior
    #
    # If sender_tx_count == 0:
    # historical average should be 0.
    # ---------------------------------------------------------

    first_sender_transactions = df[
        df["sender_tx_count"] == 0
    ]

    invalid_first_sender = (
        first_sender_transactions[
            "sender_avg_amount"
        ] != 0
    ).sum()

    print(
        "Invalid first-sender historical averages: "
        f"{invalid_first_sender}"
    )

    # ---------------------------------------------------------
    # 5. Receiver novelty
    #
    # New receivers should have zero historical
    # receiver transactions.
    # ---------------------------------------------------------

    invalid_receiver_novelty = (
        (
            df["receiver_novelty"] == 1
        )
        &
        (
            df["receiver_tx_count"] != 0
        )
    ).sum()

    print(
        "Invalid receiver novelty flags: "
        f"{invalid_receiver_novelty}"
    )

    # ---------------------------------------------------------
    # 6. Time sanity
    # ---------------------------------------------------------

    invalid_time = (
        df["time_since_prev_tx"] < -1
    ).sum()

    print(
        "Invalid time-since-previous values: "
        f"{invalid_time}"
    )

    # ---------------------------------------------------------
    # 7. Ratio sanity
    # ---------------------------------------------------------

    invalid_ratio = (
        df["sender_amount_ratio"] < 0
    ).sum()

    print(
        "Invalid sender amount ratios: "
        f"{invalid_ratio}"
    )

    # ---------------------------------------------------------
    # 8. Target distribution
    # ---------------------------------------------------------

    print("\nTarget distribution:")

    print(
        df["isFraud"].value_counts(
            normalize=False
        )
    )

    print("\nTarget percentage:")

    print(
        (
            df["isFraud"]
            .value_counts(normalize=True)
            * 100
        ).round(4)
    )

    # ---------------------------------------------------------
    # 9. Feature correlation with target
    #
    # This is NOT a model evaluation.
    # It is only a diagnostic.
    # ---------------------------------------------------------

    numeric_features = df.select_dtypes(
        include="number"
    )

    correlations = (
        numeric_features.corr()["isFraud"]
        .drop("isFraud")
        .abs()
        .sort_values(
            ascending=False
        )
    )

    print(
        "\nAbsolute correlation with fraud target:"
    )

    print(correlations)

    print("\n" + "=" * 70)
    print("Audit complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()