# FraudX AI Architecture

## Overview
FraudX AI is a multi-channel fraud and transaction risk intelligence platform. It ingests transaction data, runs feature engineering and anomaly detection, passes the data through an ensemble ML risk engine and rule-based system, and provides explainable results to analysts via a web dashboard.

## Components
1. **Frontend**: Vite + React, TypeScript, Tailwind CSS, shadcn/ui. Provides a modern SOC/SIEM-like dashboard for analysts.
2. **Backend**: FastAPI (Python). Provides REST API endpoints, handles business logic, database ORM, and integrates the ML engine.
3. **Database**: PostgreSQL. Stores users, transactions, cases, rules, and audit logs.
4. **ML Engine**: Scikit-Learn, XGBoost, Isolation Forest. Scores transactions in real-time. SHAP for explainability.
5. **Graph Engine**: NetworkX. Analyzes entity relationships (users, devices, IPs) for fraud rings.

## Deployment
Docker and Docker Compose are used to orchestrate the application locally.
