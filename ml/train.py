import os
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve, f1_score
import xgboost as xgb
from datetime import datetime

# Add backend to path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from app.database import SessionLocal
from app import models

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models'))
os.makedirs(MODEL_DIR, exist_ok=True)

def load_data():
    db = SessionLocal()
    # Read transactions into a DataFrame
    # Note: In production, query in batches or use a direct SQL-to-pandas adapter.
    query = db.query(models.Transaction)
    df = pd.read_sql(query.statement, db.bind)
    db.close()
    return df

def preprocess(df):
    if df.empty:
        raise ValueError("Dataset is empty. Run ingestion first.")
    
    # Feature engineering for ML
    df = df.copy()
    
    # Convert categorical to dummy
    if 'channel' in df.columns:
        channels_dummies = pd.get_dummies(df['channel'], prefix='channel')
        df = pd.concat([df, channels_dummies], axis=1)
        
    features = ['amount'] + [col for col in df.columns if col.startswith('channel_')]
    
    X = df[features]
    y = df['is_fraud'].astype(int)
    
    return X, y, features

def optimize_threshold(y_true, y_prob):
    # Business-cost optimized threshold
    # Cost(FP) = 5, Cost(FN) = 100
    COST_FP = 5
    COST_FN = 100
    
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    
    min_cost = float('inf')
    best_thresh = 0.5
    
    for i in range(len(thresholds)):
        thresh = thresholds[i]
        y_pred = (y_prob >= thresh).astype(int)
        
        fp = np.sum((y_pred == 1) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))
        
        cost = fp * COST_FP + fn * COST_FN
        if cost < min_cost:
            min_cost = cost
            best_thresh = thresh
            
    return best_thresh, min_cost

def train_models():
    print("Loading data from database...")
    df = load_data()
    X, y, feature_names = preprocess(df)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples.")
    
    # 1. Logistic Regression (Cost-sensitive)
    print("Training Logistic Regression...")
    lr = LogisticRegression(class_weight='balanced', random_state=42, max_iter=1000)
    lr.fit(X_train, y_train)
    
    # 2. Random Forest
    print("Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    rf.fit(X_train, y_train)
    
    # 3. XGBoost
    print("Training XGBoost...")
    # Calculate scale_pos_weight
    scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train) if sum(y_train) > 0 else 1
    xgb_model = xgb.XGBClassifier(scale_pos_weight=scale_pos_weight, eval_metric='logloss', random_state=42)
    xgb_model.fit(X_train, y_train)
    
    # 4. Anomaly Detection (Isolation Forest)
    print("Training Isolation Forest...")
    iso = IsolationForest(contamination=0.05, random_state=42)
    iso.fit(X_train)
    
    # Evaluate XGBoost and optimize threshold
    y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]
    best_thresh, expected_cost = optimize_threshold(y_test, y_prob_xgb)
    
    print(f"Optimal XGBoost Threshold: {best_thresh:.4f} (Expected Cost: {expected_cost})")
    
    # Save models
    models_dict = {
        'lr': lr,
        'rf': rf,
        'xgb': xgb_model,
        'iso': iso,
        'features': feature_names,
        'best_thresh': best_thresh
    }
    
    model_path = os.path.join(MODEL_DIR, 'fraud_models.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(models_dict, f)
        
    print(f"Models saved to {model_path}")
    
    # Write performance to DB
    db = SessionLocal()
    y_pred_optimal = (y_prob_xgb >= best_thresh).astype(int)
    
    perf = models.ModelPerformance(
        model_name="XGBoost_Hybrid",
        precision=float(classification_report(y_test, y_pred_optimal, output_dict=True)['1']['precision']),
        recall=float(classification_report(y_test, y_pred_optimal, output_dict=True)['1']['recall']),
        f1_score=float(f1_score(y_test, y_pred_optimal)),
        roc_auc=float(roc_auc_score(y_test, y_prob_xgb)),
        pr_auc=0.0, # Placeholder
        optimal_threshold=float(best_thresh),
        expected_cost=float(expected_cost)
    )
    db.add(perf)
    db.commit()
    db.close()

if __name__ == "__main__":
    train_models()
