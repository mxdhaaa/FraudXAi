import requests
import json
import uuid

URL = "http://localhost:8000/api/v1/transactions/score"

def score_txn(channel, amount, sender_id):
    payload = {
        "id": str(uuid.uuid4()),
        "channel": channel,
        "amount": amount,
        "sender_id": sender_id
    }
    
    try:
        r = requests.post(URL, json=payload)
        if r.status_code == 200:
            res = r.json()
            score_data = res.get("risk_score", {})
            print(f"[{channel} | ${amount} | {sender_id}]")
            print(f"   Fraud Prob: {score_data.get('fraud_probability'):.4f}, Anomaly: {score_data.get('anomaly_score')}, "
                  f"Behavioral: {score_data.get('behavioral_score')}")
            print(f"   Risk Score: {score_data.get('risk_score'):.2f}, Level: {score_data.get('risk_level')}, Action: {score_data.get('recommended_action')}")
            factors = score_data.get("risk_factors", [])
            for f in factors:
                print(f"     -> {f.get('human_readable')}")
        else:
            print(f"Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Request failed: {e}")
        
print("--- TESTING BACKEND RISK ENGINE ---")
score_txn("CARD", 15.0, "user_1")
score_txn("CARD", 4500.0, "user_2")
score_txn("UPI", 50.0, "user_3")
score_txn("BANK_TRANSFER", 10000.0, "user_1")
score_txn("CARD", 25.0, "user_1")
