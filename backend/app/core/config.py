"""
Core application settings and environment variables.
"""

import os
from pathlib import Path

# Paths relative to backend root
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

PORT = int(os.getenv("PORT", "8000"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BACKEND_DIR / "reliefchain.db")))
STORAGE_DIR = Path(os.getenv("STORAGE_PATH", str(BACKEND_DIR / "storage" / "uploads")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Database Environment Configuration (PostgreSQL / SQLite)
DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "reliefchain")

def get_database_url() -> str:
    """
    Constructs the database connection URL from environment variables:
    1. Direct DATABASE_URL (PostgreSQL or SQLite) if specified.
    2. PostgreSQL connection URL if POSTGRES_USER is set (never hardcoding passwords).
    3. Defaults to local SQLite database path for zero-dependency local operation.
    """
    if DATABASE_URL:
        return DATABASE_URL
    if POSTGRES_USER:
        auth = f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@" if POSTGRES_PASSWORD else f"{POSTGRES_USER}@"
        return f"postgresql://{auth}{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    return f"sqlite:///{DATABASE_PATH}"

def get_database_engine(url: str = None) -> str:
    """Returns 'postgresql' or 'sqlite' depending on the active connection URL."""
    u = url or get_database_url()
    if u.startswith("postgresql://") or u.startswith("postgres://"):
        return "postgresql"
    return "sqlite"

# MST Blockchain Testnet Parameters
MST_RPC_URL = os.getenv("MST_RPC_URL", "https://testnetrpc.mstblockchain.com")
MST_CHAIN_ID = int(os.getenv("MST_CHAIN_ID", "88888"))
MST_CONTRACT_ADDRESS = os.getenv("MST_CONTRACT_ADDRESS", "0x6c630C62D7D12CDf8a2BfEaa7995F1ce2D3937D2")
MST_PRIVATE_KEY = os.getenv("MST_PRIVATE_KEY", "")
MST_EXPLORER_URL = os.getenv("MST_EXPLORER_URL", "https://mstscan.com")
MST_FAUCET_URL = os.getenv("MST_FAUCET_URL", "https://faucet.masterstroke.academy")

# AI / CV Provider Configuration
AI_CV_PROVIDER = os.getenv("AI_CV_PROVIDER", "DEMO_CV_MODEL")

# API Versioning
API_V1_PREFIX = "/api/v1"

