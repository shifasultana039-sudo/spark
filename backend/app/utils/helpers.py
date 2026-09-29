"""
Utility helper functions for ReliefChain AI.
"""

from datetime import datetime, timezone
import hashlib

def get_current_utc_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

def sha256_checksum(data: bytes) -> str:
    """Computes standard 0x-prefixed hex SHA-256 hash."""
    return f"0x{hashlib.sha256(data).hexdigest()}"
