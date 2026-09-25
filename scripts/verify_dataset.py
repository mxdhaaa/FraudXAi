import pandas as pd
from pathlib import Path

DATA_PATH = Path("data/raw/PS_20174392719_1491204439457_log.csv")

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

print("=" * 70)
print("FraudXAi — PaySim Dataset Verification")
print("=" * 70)

total_rows = 0
fraud_count = 0
legit_count = 0
missing_counts = None
transaction_types = set()
amount_sum = 0.0
amount_min = float("inf")
amount_max = float("-inf")

chunk_size = 250_000

for chunk_number, df in enumerate(
    pd.read_csv(DATA_PATH, chunksize=chunk_size),
    start=1
):
    total_rows += len(df)

    fraud_count += int(df["isFraud"].sum())
    legit_count += int((df["isFraud"] == 0).sum())

    transaction_types.update(df["type"].dropna().unique())

    amount_sum += df["amount"].sum()
    amount_min = min(amount_min, df["amount"].min())
    amount_max = max(amount_max, df["amount"].max())

    chunk_missing = df.isna().sum()

    if missing_counts is None:
        missing_counts = chunk_missing
    else:
        missing_counts += chunk_missing

    print(f"Processed chunk {chunk_number}: {total_rows:,} rows")

fraud_rate = (fraud_count / total_rows) * 100
average_amount = amount_sum / total_rows

print("\n" + "=" * 70)
print("DATASET SUMMARY")
print("=" * 70)

print(f"Total transactions : {total_rows:,}")
print(f"Fraud transactions : {fraud_count:,}")
print(f"Legitimate         : {legit_count:,}")
print(f"Fraud rate         : {fraud_rate:.4f}%")

print(f"\nTransaction types  : {sorted(transaction_types)}")

print(f"\nAmount minimum     : {amount_min:,.2f}")
print(f"Amount maximum     : {amount_max:,.2f}")
print(f"Amount average     : {average_amount:,.2f}")

print("\nMissing values:")
print(missing_counts.to_string())

print("\nColumns:")
print(list(df.columns))

print("=" * 70)
print("Verification complete.")
print("=" * 70)