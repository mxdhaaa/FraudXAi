from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/processed/fraud_features.csv"
)

OUTPUT_DIR = Path(
    "data/processed/splits"
)

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
CHUNK_SIZE = 250_000


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {INPUT_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("FraudXAi — Chronological Dataset Split")
    print("=" * 70)

    # ---------------------------------------------------------
    # PASS 1
    # Determine chronological boundaries.
    # ---------------------------------------------------------

    total_rows = 0
    all_steps = []

    for chunk in pd.read_csv(
        INPUT_PATH,
        usecols=["step"],
        chunksize=CHUNK_SIZE,
    ):
        all_steps.append(
            chunk["step"]
        )
        total_rows += len(chunk)

    steps = pd.concat(
        all_steps,
        ignore_index=True,
    )

    train_end_index = int(
        total_rows * TRAIN_RATIO
    )

    validation_end_index = int(
        total_rows
        * (TRAIN_RATIO + VALIDATION_RATIO)
    )

    train_end_step = int(
        steps.iloc[train_end_index - 1]
    )

    validation_end_step = int(
        steps.iloc[validation_end_index - 1]
    )

    del all_steps
    del steps

    print(
        f"Total rows: {total_rows:,}"
    )

    print(
        f"Training ends at step: "
        f"{train_end_step}"
    )

    print(
        f"Validation ends at step: "
        f"{validation_end_step}"
    )

    # ---------------------------------------------------------
    # Output files
    # ---------------------------------------------------------

    train_path = (
        OUTPUT_DIR / "train.csv"
    )

    validation_path = (
        OUTPUT_DIR / "validation.csv"
    )

    test_path = (
        OUTPUT_DIR / "test.csv"
    )

    # Remove old files if they exist.
    for path in [
        train_path,
        validation_path,
        test_path,
    ]:
        if path.exists():
            path.unlink()

    # Each file needs its own header state.
    train_first_write = True
    validation_first_write = True
    test_first_write = True

    # Counters.
    train_rows = 0
    validation_rows = 0
    test_rows = 0

    train_fraud = 0
    validation_fraud = 0
    test_fraud = 0

    # ---------------------------------------------------------
    # PASS 2
    # Write chronological splits.
    # ---------------------------------------------------------

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            INPUT_PATH,
            chunksize=CHUNK_SIZE,
        ),
        start=1,
    ):

        train = chunk[
            chunk["step"] <= train_end_step
        ]

        validation = chunk[
            (chunk["step"] > train_end_step)
            & (
                chunk["step"]
                <= validation_end_step
            )
        ]

        test = chunk[
            chunk["step"] > validation_end_step
        ]

        # -----------------------------------------------------
        # TRAIN
        # -----------------------------------------------------

        if not train.empty:

            train.to_csv(
                train_path,
                mode="a",
                header=train_first_write,
                index=False,
            )

            train_first_write = False

            train_rows += len(train)

            train_fraud += int(
                train["isFraud"].sum()
            )

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if not validation.empty:

            validation.to_csv(
                validation_path,
                mode="a",
                header=validation_first_write,
                index=False,
            )

            validation_first_write = False

            validation_rows += len(
                validation
            )

            validation_fraud += int(
                validation["isFraud"].sum()
            )

        # -----------------------------------------------------
        # TEST
        # -----------------------------------------------------

        if not test.empty:

            test.to_csv(
                test_path,
                mode="a",
                header=test_first_write,
                index=False,
            )

            test_first_write = False

            test_rows += len(test)

            test_fraud += int(
                test["isFraud"].sum()
            )

        print(
            f"Processed split chunk "
            f"{chunk_number:02d}"
        )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("SPLIT SUMMARY")
    print("=" * 70)

    def report(
        name,
        rows,
        fraud,
    ):
        rate = (
            fraud / rows * 100
            if rows > 0
            else 0
        )

        print(
            f"{name:<12} | "
            f"rows={rows:,} | "
            f"fraud={fraud:,} | "
            f"fraud_rate={rate:.4f}%"
        )

    report(
        "TRAIN",
        train_rows,
        train_fraud,
    )

    report(
        "VALIDATION",
        validation_rows,
        validation_fraud,
    )

    report(
        "TEST",
        test_rows,
        test_fraud,
    )

    print("\nFiles:")
    print(train_path)
    print(validation_path)
    print(test_path)

    print("=" * 70)
    print(
        "Chronological split complete."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()