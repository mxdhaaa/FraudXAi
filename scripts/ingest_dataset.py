import uuid
from datetime import datetime, timedelta
import random
import os
import sys

# Add backend to path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from app.database import SessionLocal, engine
from app import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

class DatasetAdapter:
    def process(self, file_path: str):
        raise NotImplementedError

class DummySyntheticAdapter(DatasetAdapter):
    """Generates synthetic transactions if no CSV is provided"""
    def process(self, num_records=1000):
        transactions = []
        channels = ['CARD', 'UPI', 'BANK_TRANSFER']
        now = datetime.now()
        
        for i in range(num_records):
            is_fraud = random.random() < 0.05 # 5% fraud rate
            
            # Normal amount 10-500, fraud amount often higher (500-5000)
            amount = random.uniform(500, 5000) if is_fraud else random.uniform(10, 500)
            
            transactions.append(models.Transaction(
                id=str(uuid.uuid4()),
                timestamp=now - timedelta(minutes=random.randint(0, 10000)),
                channel=random.choice(channels),
                amount=amount,
                currency="USD",
                sender_id=f"user_{random.randint(1, 100)}",
                receiver_id=f"merchant_{random.randint(1, 50)}",
                merchant_id=f"m_{random.randint(1, 20)}",
                merchant_category="RETAIL",
                country="US",
                city="New York",
                device_id=f"dev_{random.randint(1, 200)}",
                ip_address=f"192.168.1.{random.randint(1,255)}",
                is_fraud=is_fraud
            ))
        return transactions

def main():
    print("Starting dataset ingestion...")
    db = SessionLocal()
    
    if len(sys.argv) > 1 and sys.argv[1].endswith('.csv'):
        print(f"Would parse {sys.argv[1]} but pandas is not available in minimal env.")
    else:
        print("No CSV provided, generating synthetic data...")
        adapter = DummySyntheticAdapter()
        transactions = adapter.process(1000)
        
        # Batch insert
        db.bulk_save_objects(transactions)
        db.commit()
        print(f"Inserted {len(transactions)} synthetic records.")
    
    db.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    main()
