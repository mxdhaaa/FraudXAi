from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api import api_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FraudX AI - Risk Engine API",
    description="Multi-channel transaction risk intelligence API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For codeathon purposes, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
