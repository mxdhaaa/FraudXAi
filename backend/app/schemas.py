from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TransactionBase(BaseModel):
    id: str
    channel: str
    amount: float
    currency: Optional[str] = "USD"
    sender_id: str
    receiver_id: Optional[str] = None
    merchant_id: Optional[str] = None
    merchant_category: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_fraud: Optional[bool] = False

class TransactionCreate(TransactionBase):
    pass

class RiskScoreResponse(BaseModel):
    risk_score: float
    risk_level: str
    recommended_action: str
    fraud_probability: float
    anomaly_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    risk_factors: Optional[List[Dict[str, Any]]] = None
    triggered_rules: Optional[List[str]] = None

class TransactionResponse(TransactionBase):
    risk_score: Optional[RiskScoreResponse] = None

    class Config:
        from_attributes = True

class BatchTransactionRequest(BaseModel):
    transactions: List[TransactionCreate]

class CaseResponse(BaseModel):
    id: int
    transaction_id: str
    status: str
    priority: str
    analyst_id: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
