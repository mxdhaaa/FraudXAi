from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path(
    "data/raw/PS_20174392719_1491204439457_log.csv"
)

OUTPUT_PATH = Path(
    "data/processed/fraud_features.csv"
)

CHUNK_SIZE = 250_000


TYPE_MAP = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}


FEATURE_COLUMNS = [
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
    "isFraud",
]


def build_chunk_features(
    df: pd.DataFrame,
    sender_state: dict,
    receiver_state: dict,
) -> pd.DataFrame:
    """
    Build behavioral features using only information available
    before each transaction.

    sender_state:
        sender -> {
            count,
            amount_sum,
            last_step,
            type_counts
        }

    receiver_state:
        receiver -> transaction count
    """

    rows = []

    for row in df.itertuples(index=False):

        sender = row.nameOrig
        receiver = row.nameDest

        amount = float(row.amount)
        step = int(row.step)

        # -----------------------------------------------------
        # Previous sender history
        # -----------------------------------------------------

        sender_info = sender_state.get(
            sender,
            {
                "count": 0,
                "amount_sum": 0.0,
                "last_step": None,
                "type_counts": {},
            },
        )

        sender_count = sender_info["count"]

        if sender_count > 0:
            sender_avg_amount = (
                sender_info["amount_sum"] / sender_count
            )
        else:
            sender_avg_amount = 0.0

        if sender_avg_amount > 0:
            sender_amount_ratio = (
                amount / sender_avg_amount
            )
        else:
            sender_amount_ratio = 0.0

        if sender_info["last_step"] is None:
            time_since_prev_tx = -1
        else:
            time_since_prev_tx = (
                step - sender_info["last_step"]
            )

        rapid_repeat = int(
            0 <= time_since_prev_tx <= 1
        )

        transaction_type = row.type

        sender_type_tx_count = sender_info[
            "type_counts"
        ].get(transaction_type, 0)

        # -----------------------------------------------------
        # Previous receiver history
        # -----------------------------------------------------

        receiver_count = receiver_state.get(
            receiver,
            0,
        )

        receiver_novelty = int(
            receiver_count == 0
        )

        # -----------------------------------------------------
        # Balance consistency
        # -----------------------------------------------------

        origin_balance_error = abs(
            float(row.oldbalanceOrg)
            - amount
            - float(row.newbalanceOrig)
        )

        destination_balance_error = abs(
            float(row.oldbalanceDest)
            + amount
            - float(row.newbalanceDest)
        )

        # -----------------------------------------------------
        # Construct feature row
        # -----------------------------------------------------

        feature_row = {
            "step": step,

            "hour": (step - 1) % 24,

            "day": (step - 1) // 24,

            "amount": amount,

            "log_amount": np.log1p(amount),

            "oldbalanceOrg": float(
                row.oldbalanceOrg
            ),

            "newbalanceOrig": float(
                row.newbalanceOrig
            ),

            "oldbalanceDest": float(
                row.oldbalanceDest
            ),

            "newbalanceDest": float(
                row.newbalanceDest
            ),

            "origin_balance_error": (
                origin_balance_error
            ),

            "destination_balance_error": (
                destination_balance_error
            ),

            "type_code": TYPE_MAP.get(
                transaction_type,
                -1,
            ),

            "sender_tx_count": sender_count,

            "sender_avg_amount": (
                sender_avg_amount
            ),

            "sender_amount_ratio": (
                sender_amount_ratio
            ),

            "time_since_prev_tx": (
                time_since_prev_tx
            ),

            "rapid_repeat": rapid_repeat,

            "receiver_tx_count": (
                receiver_count
            ),

            "receiver_novelty": (
                receiver_novelty
            ),

            "sender_type_tx_count": (
                sender_type_tx_count
            ),

            "isFraud": int(row.isFraud),
        }

        rows.append(feature_row)

        # -----------------------------------------------------
        # UPDATE STATE AFTER feature calculation
        #
        # This is critical:
        # the current transaction must NOT influence its
        # own historical features.
        # -----------------------------------------------------

        if sender not in sender_state:
            sender_state[sender] = {
                "count": 0,
                "amount_sum": 0.0,
                "last_step": None,
                "type_counts": {},
            }

        sender_state[sender]["count"] += 1

        sender_state[sender]["amount_sum"] += amount

        sender_state[sender]["last_step"] = step

        sender_state[sender]["type_counts"][
            transaction_type
        ] = (
            sender_state[sender]["type_counts"]
            .get(transaction_type, 0)
            + 1
        )

        receiver_state[receiver] = (
            receiver_state.get(receiver, 0) + 1
        )

    return pd.DataFrame(
        rows,
        columns=FEATURE_COLUMNS,
    )


def main():

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_PATH}"
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove previous generated dataset.
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    sender_state = {}
    receiver_state = {}

    total_rows = 0

    print("=" * 70)
    print("FraudXAi — Stateful Behavioral Feature Pipeline")
    print("=" * 70)

    reader = pd.read_csv(
        INPUT_PATH,
        chunksize=CHUNK_SIZE,
    )
    
    for chunk_number, chunk in enumerate(
        reader,
        start=1,
    ):

        features = build_chunk_features(
            chunk,
            sender_state,
            receiver_state,
        )

        features.to_csv(
            OUTPUT_PATH,
            mode="a",
            header=chunk_number == 1,
            index=False,
        )

        total_rows += len(features)

        print(
            f"Chunk {chunk_number:02d} | "
            f"rows: {total_rows:,} | "
            f"senders tracked: {len(sender_state):,} | "
            f"receivers tracked: {len(receiver_state):,}"
        )

    print("\n" + "=" * 70)
    print("Feature engineering complete.")
    print("=" * 70)

    print(
        f"Total rows generated: {total_rows:,}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()