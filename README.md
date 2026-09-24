# FraudX AI

Transaction Risk Intelligence Platform designed for the Codeathon.

## Features
- Multi-channel fraud detection (Cards, UPI, Bank Transfer)
- Fast inference API (FastAPI)
- Modern Dashboard (Vite + React + Tailwind)
- Business-cost optimization thresholds

## Installation

### Backend
1. `cd backend`
2. `python -m venv .venv`
3. `.\.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux)
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` (it defaults to the bundled local SQLite database).

### Database Seeding
To generate 1000 synthetic transactions in local SQLite database:
`python ../scripts/ingest_dataset.py`

### Run Backend
`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

To use Docker PostgreSQL instead, start `docker compose up -d db` from the project root and set `DATABASE_URL` to the PostgreSQL URL in `backend/.env.example`.

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm run dev`

Visit `http://localhost:5173`
