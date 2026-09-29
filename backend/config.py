"""
Configuration settings for ReliefChain AI backend.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

PORT = int(os.getenv("PORT", "8000"))
DATABASE_PATH = BASE_DIR / "reliefchain.db"
STORAGE_DIR = BASE_DIR / "storage" / "uploads"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# MST Blockchain Testnet Parameters
MST_RPC_URL = os.getenv("MST_RPC_URL", "https://testnetrpc.mstblockchain.com")
MST_CHAIN_ID = int(os.getenv("MST_CHAIN_ID", "88888"))
MST_CONTRACT_ADDRESS = os.getenv("MST_CONTRACT_ADDRESS", "0x84AB4dC72536D55aDa9617b673dd33AC9d709d14")
MST_PRIVATE_KEY = os.getenv("MST_PRIVATE_KEY", "")
MST_EXPLORER_URL = os.getenv("MST_EXPLORER_URL", "https://mstscan.com")
MST_FAUCET_URL = os.getenv("MST_FAUCET_URL", "https://faucet.masterstroke.academy")
BRIDGEKEY_URL = os.getenv("BRIDGEKEY_URL", "https://bridgekey.io")

# AI CV Provider
AI_CV_PROVIDER = os.getenv("AI_CV_PROVIDER", "DEMO_CV_MODEL")
