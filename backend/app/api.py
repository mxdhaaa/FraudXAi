import os
import pickle
import pandas as pd
import numpy as np
import shap
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from . import models, schemas
from .database import get_db

api_router = APIRouter()

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/models'))
MODEL_PATH = os.path.join(MODEL_DIR, 'fraud_models.pkl')

# Global ML models
fraud_models = None
explainer = None

def load_models():
    global fraud_models, explainer
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                fraud_models = pickle.load(f)
            # Initialize SHAP explainer
            xgb_model = fraud_models['xgb']
            explainer = shap.TreeExplainer(xgb_model)
            print("Successfully loaded ML models and SHAP explainer.")
        except Exception as e:
            print(f"Error loading models: {e}")
    else:
        print("Warning: fraud_models.pkl not found. ML features will fail.")

load_models()


def transaction_response(transaction: models.Transaction) -> dict:
    """Serialize ORM instances consistently on both Pydantic v1 and v2."""
    if hasattr(schemas.TransactionResponse, "model_validate"):
        return schemas.TransactionResponse.model_validate(transaction).model_dump()
    return schemas.TransactionResponse.from_orm(transaction).dict()

def extract_behavioral_signals(db: Session, sender_id: str, current_amount: float) -> dict:
    """Calculates behavioral signals for a user based on historical transactions."""
    past_txns = db.query(models.Transaction).filter(models.Transaction.sender_id == sender_id).all()
    
    if not past_txns:
        return {
            "amount_deviation": 0.0,
            "is_unusual_amount": False,
            "historical_count": 0,
            "behavioral_score": 0.5  # Neutral default
        }
        
    amounts = [t.amount for t in past_txns if t.amount is not None]
    if not amounts:
        return {"amount_deviation": 0.0, "is_unusual_amount": False, "historical_count": 0, "behavioral_score": 0.5}
        
    median_amount = np.median(amounts)
    std_amount = np.std(amounts) if len(amounts) > 1 else 0
    
    deviation = current_amount - median_amount
    is_unusual = std_amount > 0 and abs(deviation) > (3 * std_amount)
    
    # Simple behavioral score (0-1): higher means more unusual
    score = 0.5
    if is_unusual and deviation > 0:
        score = 0.9 # High amount deviation
    elif is_unusual:
        score = 0.8 # Unusual but not high amount
    elif len(past_txns) > 5 and abs(deviation) < std_amount:
        score = 0.1 # Very consistent
        
    return {
        "amount_deviation": deviation,
        "is_unusual_amount": is_unusual,
        "historical_count": len(past_txns),
        "behavioral_score": score
    }

@api_router.post("/transactions/score", response_model=schemas.TransactionResponse)
def score_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    if fraud_models is None:
        raise HTTPException(status_code=503, detail="ML models are unavailable. Train the model before scoring transactions.")

    # Evaluate the incoming transaction against prior behaviour, before it is saved.
    behavior = extract_behavioral_signals(db, transaction.sender_id, transaction.amount)

    # 1. Save transaction
    db_txn = models.Transaction(**transaction.dict(exclude_unset=True))
    db.add(db_txn)
    try:
        db.commit()
        db.refresh(db_txn)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="A transaction with this id already exists")
        
    xgb_model = fraud_models['xgb']
    iso_model = fraud_models['iso']
    features = fraud_models['features']
    best_thresh = fraud_models.get('best_thresh', 0.5)
    
    # 2. Create DataFrame for ML
    sample_data = {
        'amount': [db_txn.amount],
        f'channel_{db_txn.channel}': [1]
    }
    
    df = pd.DataFrame(sample_data)
    for f in features:
        if f not in df.columns:
            df[f] = 0
    df = df[features]
    
    # 3. Predict
    fraud_prob = float(xgb_model.predict_proba(df)[0, 1])
    iso_pred = iso_model.predict(df)[0]
    
    # Isolation forest returns -1 for anomaly, 1 for normal.
    # Convert to a 0-1 anomaly score
    anomaly_score = 1.0 if iso_pred == -1 else 0.0 
    
    # 4. Risk Engine Combining Logic
    # Weighting: 60% XGBoost, 20% Anomaly, 20% Behavioral
    risk_score_raw = (fraud_prob * 0.6) + (anomaly_score * 0.2) + (behavior["behavioral_score"] * 0.2)
    risk_score_100 = min(100.0, max(0.0, risk_score_raw * 100))
    
    # Risk Level & Action based on dynamic thresholding
    # Map threshold space (0 to best_thresh) to (0 to 75)
    # Map threshold space (best_thresh to 1.0) to (75 to 100)
    
    if fraud_prob >= best_thresh or risk_score_100 >= 75:
        risk_level = "HIGH"
        action = "BLOCK"
    elif fraud_prob >= (best_thresh * 0.5) or risk_score_100 >= 50:
        risk_level = "MEDIUM"
        action = "REVIEW"
    else:
        risk_level = "LOW"
        action = "APPROVE"
        
    # 5. Explainability (SHAP + Rules)
    risk_factors = []
    
    if explainer is not None:
        shap_values = explainer.shap_values(df)
        if isinstance(shap_values, list):
            shap_values = shap_values[-1]
        # Sort features by absolute SHAP impact
        feature_impacts = [(f, float(val)) for f, val in zip(features, shap_values[0])]
        feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for f, impact in feature_impacts[:3]:
            if abs(impact) > 0.05: # Only show significant factors
                desc = f"Transaction amount (${db_txn.amount})" if f == 'amount' else f"Channel: {f.replace('channel_', '')}"
                risk_factors.append({
                    "feature": f,
                    "description": desc,
                    "impact": impact,
                    "human_readable": f"High risk contribution from {desc} (impact: {impact:+.2f})" if impact > 0 else f"Safety signal from {desc} (impact: {impact:+.2f})"
                })
                
    # Add behavioral rules
    if behavior["is_unusual_amount"]:
        risk_factors.append({
            "feature": "behavioral_amount",
            "description": "Unusual Transaction Amount",
            "impact": 0.5,
            "human_readable": f"Amount is significantly higher than user's normal baseline (Deviation: +${behavior['amount_deviation']:.2f})"
        })
        
    if anomaly_score == 1.0:
        risk_factors.append({
            "feature": "isolation_forest",
            "description": "Multivariate Anomaly",
            "impact": 0.8,
            "human_readable": "Transaction is highly anomalous compared to global baseline patterns."
        })
        
    # 6. Save Risk Score
    db_risk = models.RiskScore(
        transaction_id=db_txn.id,
        score=risk_score_100,  # Map to existing DB column
        risk_level=risk_level,
        decision=action,       # Map to existing DB column
        model_probability=fraud_prob, # Map to existing DB column
        risk_factors=risk_factors,
        triggered_rules=["UNUSUAL_AMOUNT"] if behavior["is_unusual_amount"] else []
    )
    db.add(db_risk)
    db.commit()
    db.refresh(db_txn)
    
    # We construct the Pydantic schema manually to match the requested fields precisely
    txn_dict = transaction_response(db_txn)
    
    # Override risk_score mapping to use the updated schema format for the response
    txn_dict["risk_score"] = schemas.RiskScoreResponse(
        risk_score=risk_score_100,
        risk_level=risk_level,
        recommended_action=action,
        fraud_probability=fraud_prob,
        anomaly_score=anomaly_score,
        behavioral_score=behavior["behavioral_score"],
        risk_factors=risk_factors,
        triggered_rules=db_risk.triggered_rules
    )
    
    return txn_dict

@api_router.get("/transactions", response_model=List[schemas.TransactionResponse])
def get_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Manual mapping to align with new schema response if needed
    result = []
    for t in transactions:
        t_dict = transaction_response(t)
        if t.risk_score:
            t_dict["risk_score"] = schemas.RiskScoreResponse(
                risk_score=t.risk_score.score,
                risk_level=t.risk_score.risk_level,
                recommended_action=t.risk_score.decision,
                fraud_probability=t.risk_score.model_probability,
                risk_factors=t.risk_score.risk_factors,
                triggered_rules=t.risk_score.triggered_rules
            )
        result.append(t_dict)
    return result

@api_router.get("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    t_dict = transaction_response(t)
    if t.risk_score:
        t_dict["risk_score"] = schemas.RiskScoreResponse(
            risk_score=t.risk_score.score,
            risk_level=t.risk_score.risk_level,
            recommended_action=t.risk_score.decision,
            fraud_probability=t.risk_score.model_probability,
            risk_factors=t.risk_score.risk_factors,
            triggered_rules=t.risk_score.triggered_rules
        )
    return t_dict

@api_router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(models.Transaction).count()
    fraud = db.query(models.RiskScore).filter(models.RiskScore.decision == "BLOCK").count()
    
    amount_at_risk = db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).join(
        models.RiskScore, models.RiskScore.transaction_id == models.Transaction.id
    ).filter(models.RiskScore.decision == "BLOCK").scalar()

    return {
        "total_transactions": total,
        "fraud_detected": fraud,
        "amount_at_risk": float(amount_at_risk),
        "active_investigations": db.query(models.Case).filter(models.Case.status != "CLOSED").count()
    }

@api_router.get("/cases", response_model=List[schemas.CaseResponse])
def get_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cases = db.query(models.Case).offset(skip).limit(limit).all()
    return cases
