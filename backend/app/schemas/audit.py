"""
ReliefChain AI - Audit & Integrity Schemas (Step 10).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """Normalized audit log event model."""
    id: int
    record_id: str
    audit_id: Optional[str] = None
    timestamp: str
    previous_record_hash: str
    current_record_hash: str
    evidence_hash: Optional[str] = None
    event_type: str
    actor: str
    actor_id: Optional[str] = None
    role: Optional[str] = "CITIZEN"
    entity_type: str
    entity_id: str
    description: str
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    is_valid: bool = True

    class Config:
        from_attributes = True


class AuditHistoryResponse(BaseModel):
    """Paged audit history response with privacy filtering."""
    total_records: int
    limit: int
    offset: int
    records: List[AuditEventResponse]


class AuditIntegrityVerificationResponse(BaseModel):
    """Cryptographic chain verification outcome."""
    chain_valid: bool
    tampered: bool = False
    total_events: int
    status: str
    latest_head_hash: Optional[str] = None
    broken_at_id: Optional[int] = None
    broken_at_record_id: Optional[str] = None
    error_type: Optional[str] = None
    error: Optional[str] = None
    expected_hash: Optional[str] = None
    found_hash: Optional[str] = None
    verified_at: Optional[str] = None
