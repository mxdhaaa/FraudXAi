import os
import sys
import pickle
import pandas as pd

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ml/models'))
model_path = os.path.join(MODEL_DIR, 'fraud_models.pkl')

def test_prediction():
    print(f"Loading model from {model_path}...")
    with open(model_path, 'rb') as f:
        models_dict = pickle.load(f)
        
    xgb_model = models_dict['xgb']
    features = models_dict['features']
    best_thresh = models_dict['best_thresh']
    
    print(f"Model loaded successfully. Optimal threshold is: {best_thresh:.4f}")
    
    # Create a synthetic high-risk transaction
    # amount is large, let's say 4500. Channel is CARD.
    sample_data = {
        'amount': [4500.0],
        'channel_CARD': [1],
        'channel_UPI': [0],
        'channel_BANK_TRANSFER': [0]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Ensure all features match
    for f in features:
        if f not in df.columns:
            df[f] = 0
    df = df[features]
    
    prob = xgb_model.predict_proba(df)[0, 1]
    is_fraud = int(prob >= best_thresh)
    
    print("--- Test Prediction Result ---")
    print(f"Transaction Amount: $4500, Channel: CARD")
    print(f"Fraud Probability: {prob:.4f}")
    print(f"Decision (Threshold {best_thresh:.4f}): {'FRAUD (DECLINE)' if is_fraud else 'SAFE (APPROVE)'}")

if __name__ == "__main__":
    test_prediction()
