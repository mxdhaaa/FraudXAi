from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    channel = Column(String, index=True) # CARD, UPI, BANK_TRANSFER, etc.
    amount = Column(Float)
    currency = Column(String)
    sender_id = Column(String, index=True)
    receiver_id = Column(String, index=True, nullable=True)
    merchant_id = Column(String, index=True, nullable=True)
    merchant_category = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Ground truth for evaluation
    is_fraud = Column(Boolean, default=False)
    
    risk_score = relationship("RiskScore", back_populates="transaction", uselist=False)

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    score = Column(Float)
    risk_level = Column(String) # LOW, GUARDED, MEDIUM, HIGH, CRITICAL
    decision = Column(String) # APPROVE, REVIEW, BLOCK
    model_probability = Column(Float)
    
    # JSON field storing SHAP values or top reasons
    risk_factors = Column(JSON, nullable=True) 
    
    # JSON field storing triggered rules
    triggered_rules = Column(JSON, nullable=True)
    
    evaluated_at = Column(DateTime(timezone=True), default=func.now())
    
    transaction = relationship("Transaction", back_populates="risk_score")

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    status = Column(String, default="NEW") # NEW, UNDER REVIEW, CONFIRMED FRAUD, FALSE POSITIVE
    priority = Column(String, default="MEDIUM")
    analyst_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    transaction = relationship("Transaction")

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String)
    evaluated_at = Column(DateTime(timezone=True), default=func.now())
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)
    pr_auc = Column(Float)
    optimal_threshold = Column(Float)
    expected_cost = Column(Float)
