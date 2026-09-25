from fastapi import APIRouter, Depends, HTTPException
import os
from typing import List

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db


api_router = APIRouter()


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../ml/models")
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "receiver_behavioral_xgboost.json"
)

MODEL_FEATURES = [
    "amount",
    "log_amount",
    "type_code",
    "hour",
    "day",
    "step",
    "receiver_tx_count",
    "receiver_novelty",
]

TYPE_MAPPING = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}


# ============================================================
# GLOBAL MODEL
# ============================================================

fraud_model = None
explainer = None


def load_models():
    """
    Load the validated receiver-focused XGBoost model
    and initialize its SHAP TreeExplainer.
    """
    global fraud_model, explainer

    if not os.path.exists(MODEL_PATH):
        print(f"Warning: model not found: {MODEL_PATH}")
        return

    try:
        fraud_model = xgb.XGBClassifier()
        fraud_model.load_model(MODEL_PATH)

        explainer = shap.TreeExplainer(fraud_model)

        print(
            "Successfully loaded receiver-focused "
            "XGBoost model and SHAP explainer."
        )

    except Exception as e:
        fraud_model = None
        explainer = None
        print(f"Error loading receiver-focused model: {e}")


load_models()


# ============================================================
# RESPONSE HELPERS
# ============================================================

def transaction_response(transaction: models.Transaction) -> dict:
    return {
        "id": transaction.id,
        "channel": transaction.channel,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "sender_id": transaction.sender_id,
        "receiver_id": transaction.receiver_id,
        "merchant_id": transaction.merchant_id,
        "merchant_category": transaction.merchant_category,
        "country": transaction.country,
        "city": transaction.city,
        "device_id": transaction.device_id,
        "ip_address": transaction.ip_address,
        "timestamp": transaction.timestamp,
        "is_fraud": transaction.is_fraud,
        "risk_score": None,
    }
    """
    Serialize a transaction while explicitly converting the
    SQLAlchemy RiskScore relationship into the API schema.
    """

    if hasattr(
        schemas.TransactionResponse,
        "model_validate",
    ):
        data = schemas.TransactionResponse.model_validate(
            transaction
        ).model_dump()

    else:
        data = schemas.TransactionResponse.from_orm(
            transaction
        ).dict()

    # Replace the ORM RiskScore object with a serializable
    # RiskScoreResponse dictionary.
    if transaction.risk_score is not None:
        data["risk_score"] = (
            schemas.RiskScoreResponse(
                risk_score=transaction.risk_score.score,
                risk_level=transaction.risk_score.risk_level,
                recommended_action=(
                    transaction.risk_score.decision
                ),
                fraud_probability=(
                    transaction.risk_score.model_probability
                ),
                anomaly_score=None,
                behavioral_score=None,
                risk_factors=(
                    transaction.risk_score.risk_factors
                ),
                triggered_rules=(
                    transaction.risk_score.triggered_rules
                ),
            ).model_dump()
            if hasattr(
                schemas.RiskScoreResponse,
                "model_dump",
            )
            else schemas.RiskScoreResponse(
                risk_score=transaction.risk_score.score,
                risk_level=transaction.risk_score.risk_level,
                recommended_action=(
                    transaction.risk_score.decision
                ),
                fraud_probability=(
                    transaction.risk_score.model_probability
                ),
                anomaly_score=None,
                behavioral_score=None,
                risk_factors=(
                    transaction.risk_score.risk_factors
                ),
                triggered_rules=(
                    transaction.risk_score.triggered_rules
                ),
            ).dict()
        )

    return data


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def build_model_features(
    db: Session,
    transaction: models.Transaction,
) -> tuple[pd.DataFrame, dict]:
    """
    Build the exact eight features expected by the
    receiver-focused XGBoost model.

    The receiver history is calculated before the current
    transaction is counted.
    """

    transaction_type = transaction.channel.upper()

    if transaction_type not in TYPE_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported transaction type: "
                f"{transaction.channel}. "
                f"Use one of: {', '.join(TYPE_MAPPING.keys())}"
            ),
        )

    type_code = TYPE_MAPPING[transaction_type]

    # --------------------------------------------------------
    # PaySim temporal representation
    # --------------------------------------------------------
    #
    # The experimental dataset uses "step" rather than an
    # exact timestamp. The API therefore derives a simple
    # step representation from the transaction timestamp.
    #
    # This is a demo/API representation and should not be
    # interpreted as an exact reconstruction of PaySim step.
    # --------------------------------------------------------

    if transaction.timestamp is not None:
        step = (
            (transaction.timestamp.day - 1) * 24
            + transaction.timestamp.hour
            + 1
        )
    else:
        step = 1

    hour = (step - 1) % 24
    day = (step - 1) // 24

    # --------------------------------------------------------
    # Receiver behavioral history
    # --------------------------------------------------------

    if transaction.receiver_id:
        receiver_history = (
            db.query(models.Transaction)
            .filter(
                models.Transaction.receiver_id
                == transaction.receiver_id,
                models.Transaction.id != transaction.id,
            )
            .all()
        )
    else:
        receiver_history = []

    receiver_tx_count = len(receiver_history)

    receiver_novelty = (
        1 if receiver_tx_count == 0 else 0
    )

    # --------------------------------------------------------
    # Model features
    # --------------------------------------------------------

    amount = float(transaction.amount)

    sample_data = {
        "amount": [amount],
        "log_amount": [
            float(np.log1p(max(amount, 0)))
        ],
        "type_code": [type_code],
        "hour": [hour],
        "day": [day],
        "step": [step],
        "receiver_tx_count": [receiver_tx_count],
        "receiver_novelty": [receiver_novelty],
    }

    df = pd.DataFrame(sample_data)[MODEL_FEATURES]

    metadata = {
        "transaction_type": transaction_type,
        "type_code": type_code,
        "step": step,
        "hour": hour,
        "day": day,
        "receiver_tx_count": receiver_tx_count,
        "receiver_novelty": receiver_novelty,
    }

    return df, metadata


# ============================================================
# SHAP EXPLANATION
# ============================================================

def generate_shap_factors(
    df: pd.DataFrame,
    transaction: models.Transaction,
    metadata: dict,
) -> list:
    """
    Generate individual-prediction SHAP explanations.
    """

    if explainer is None:
        return []

    shap_values = explainer.shap_values(df)

    if isinstance(shap_values, list):
        shap_values = shap_values[-1]

    shap_row = np.asarray(shap_values)[0]

    feature_impacts = [
        (feature, float(impact))
        for feature, impact in zip(
            MODEL_FEATURES,
            shap_row,
        )
    ]

    feature_impacts.sort(
        key=lambda item: abs(item[1]),
        reverse=True,
    )

    receiver_count = metadata["receiver_tx_count"]
    receiver_novelty = metadata["receiver_novelty"]
    transaction_type = metadata["transaction_type"]

    feature_descriptions = {
        "amount": (
            f"Transaction amount: "
            f"{transaction.amount:.2f}"
        ),

        "log_amount": (
            "Log-transformed transaction amount"
        ),

        "type_code": (
            f"Transaction type: "
            f"{transaction_type}"
        ),

        "hour": (
            f"Transaction hour: "
            f"{metadata['hour']}"
        ),

        "day": (
            f"Transaction day index: "
            f"{metadata['day']}"
        ),

        "step": (
            f"PaySim step: "
            f"{metadata['step']}"
        ),

        "receiver_tx_count": (
            "Receiver transaction history: "
            f"{receiver_count} previous transactions"
        ),

        "receiver_novelty": (
            "Receiver has no prior transaction history"
            if receiver_novelty == 1
            else "Receiver has prior transaction history"
        ),
    }

    risk_factors = []

    for feature, impact in feature_impacts[:5]:

        if abs(impact) < 0.05:
            continue

        description = feature_descriptions.get(
            feature,
            feature,
        )

        direction = (
            "increases fraud risk"
            if impact > 0
            else "decreases fraud risk"
        )

        risk_factors.append(
            {
                "feature": feature,
                "description": description,
                "impact": impact,
                "human_readable": (
                    f"{description} "
                    f"{direction} "
                    f"(SHAP impact: {impact:+.2f})"
                ),
            }
        )

    return risk_factors


# ============================================================
# DECISION POLICY
# ============================================================

def apply_decision_policy(
    fraud_probability: float,
) -> tuple[float, str, str]:
    """
    Apply the frozen validation decision policy.

    APPROVE : probability < 0.60
    REVIEW  : 0.60 <= probability < 0.95
    BLOCK   : probability >= 0.95
    """

    risk_score = fraud_probability * 100.0

    if fraud_probability >= 0.95:
        return risk_score, "HIGH", "BLOCK"

    if fraud_probability >= 0.60:
        return risk_score, "MEDIUM", "REVIEW"

    return risk_score, "LOW", "APPROVE"


# ============================================================
# SCORE TRANSACTION
# ============================================================

@api_router.post(
    "/transactions/score",
    response_model=schemas.TransactionResponse,
)
def score_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
):

    if fraud_model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Receiver-focused XGBoost model "
                "is unavailable."
            ),
        )

    # --------------------------------------------------------
    # Save transaction
    # --------------------------------------------------------

    db_txn = models.Transaction(
        **transaction.dict(exclude_unset=True)
    )

    db.add(db_txn)

    try:
        db.commit()
        db.refresh(db_txn)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "A transaction with this id "
                "already exists"
            ),
        )

    # --------------------------------------------------------
    # Build model features
    # --------------------------------------------------------

    df, metadata = build_model_features(
        db,
        db_txn,
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    fraud_probability = float(
        fraud_model.predict_proba(df)[0, 1]
    )

    # --------------------------------------------------------
    # Decision policy
    # --------------------------------------------------------

    risk_score_100, risk_level, action = (
        apply_decision_policy(
            fraud_probability
        )
    )

    # --------------------------------------------------------
    # SHAP explanation
    # --------------------------------------------------------

    risk_factors = generate_shap_factors(
        df,
        db_txn,
        metadata,
    )

    # --------------------------------------------------------
    # Triggered rules
    # --------------------------------------------------------

    triggered_rules = []

    if metadata["receiver_novelty"] == 1:
        triggered_rules.append(
            "NEW_RECEIVER"
        )

    if action == "REVIEW":
        triggered_rules.append(
            "HUMAN_REVIEW_REQUIRED"
        )

    if action == "BLOCK":
        triggered_rules.append(
            "HIGH_RISK_BLOCK"
        )

    # --------------------------------------------------------
    # Save risk score
    # --------------------------------------------------------

    db_risk = models.RiskScore(
        transaction_id=db_txn.id,
        score=risk_score_100,
        risk_level=risk_level,
        decision=action,
        model_probability=fraud_probability,
        risk_factors=risk_factors,
        triggered_rules=triggered_rules,
    )

    db.add(db_risk)

    # --------------------------------------------------------
    # Create investigation case for REVIEW
    # --------------------------------------------------------

    if action == "REVIEW":
        review_case = models.Case(
            transaction_id=db_txn.id,
            status="NEW",
            priority="HIGH",
            notes=(
                "Model recommends manual review. "
                "Final decision must be made by a human investigator."
            ),
        )

        db.add(review_case)

    db.commit()
    db.refresh(db_txn)

    # --------------------------------------------------------
    # Build API response
    # --------------------------------------------------------

    txn_dict = transaction_response(db_txn)

    txn_dict["risk_score"] = (
        schemas.RiskScoreResponse(
            risk_score=risk_score_100,
            risk_level=risk_level,
            recommended_action=action,
            fraud_probability=fraud_probability,
            anomaly_score=None,
            behavioral_score=None,
            risk_factors=risk_factors,
            triggered_rules=triggered_rules,
        )
    )

    return txn_dict


# ============================================================
# TRANSACTION LIST
# ============================================================

@api_router.get(
    "/transactions",
    response_model=List[schemas.TransactionResponse],
)
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):

    transactions = (
        db.query(models.Transaction)
        .order_by(
            models.Transaction.timestamp.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []

    for transaction in transactions:

        txn_dict = transaction_response(
            transaction
        )

        if transaction.risk_score:

            txn_dict["risk_score"] = (
                schemas.RiskScoreResponse(
                    risk_score=(
                        transaction.risk_score.score
                    ),
                    risk_level=(
                        transaction.risk_score.risk_level
                    ),
                    recommended_action=(
                        transaction.risk_score.decision
                    ),
                    fraud_probability=(
                        transaction.risk_score.model_probability
                    ),
                    anomaly_score=None,
                    behavioral_score=None,
                    risk_factors=(
                        transaction.risk_score.risk_factors
                    ),
                    triggered_rules=(
                        transaction.risk_score.triggered_rules
                    ),
                )
            )

        result.append(txn_dict)

    return result


# ============================================================
# SINGLE TRANSACTION
# ============================================================

@api_router.get(
    "/transactions/{transaction_id}",
    response_model=schemas.TransactionResponse,
)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):

    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    txn_dict = transaction_response(
        transaction
    )

    if transaction.risk_score:

        txn_dict["risk_score"] = (
            schemas.RiskScoreResponse(
                risk_score=(
                    transaction.risk_score.score
                ),
                risk_level=(
                    transaction.risk_score.risk_level
                ),
                recommended_action=(
                    transaction.risk_score.decision
                ),
                fraud_probability=(
                    transaction.risk_score.model_probability
                ),
                anomaly_score=None,
                behavioral_score=None,
                risk_factors=(
                    transaction.risk_score.risk_factors
                ),
                triggered_rules=(
                    transaction.risk_score.triggered_rules
                ),
            )
        )

    return txn_dict


# ============================================================
# DASHBOARD
# ============================================================

@api_router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
):

    total = (
        db.query(models.Transaction)
        .count()
    )

    fraud = (
        db.query(models.RiskScore)
        .filter(
            models.RiskScore.decision == "BLOCK"
        )
        .count()
    )

    amount_at_risk = (
        db.query(
            func.coalesce(
                func.sum(
                    models.Transaction.amount
                ),
                0.0,
            )
        )
        .join(
            models.RiskScore,
            models.RiskScore.transaction_id
            == models.Transaction.id,
        )
        .filter(
            models.RiskScore.decision == "BLOCK"
        )
        .scalar()
    )

    active_investigations = (
        db.query(models.Case)
        .filter(
            models.Case.status != "CLOSED"
        )
        .count()
    )

    return {
        "total_transactions": total,
        "fraud_detected": fraud,
        "amount_at_risk": float(
            amount_at_risk
        ),
        "active_investigations": (
            active_investigations
        ),
    }


# ============================================================
# INVESTIGATION CASES
# ============================================================

@api_router.get(
    "/cases",
    response_model=List[schemas.CaseResponse],
)
def get_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):

    cases = (
        db.query(models.Case)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return cases
@api_router.patch(
    "/cases/{case_id}",
    response_model=schemas.CaseResponse,
)
def update_case(
    case_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    case = (
        db.query(models.Case)
        .filter(models.Case.id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    allowed_statuses = {
        "CONFIRMED_FRAUD",
        "CONFIRMED_LEGITIMATE",
        "ESCALATED",
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid case status",
        )

    case.status = status
    db.commit()
    db.refresh(case)

    return case