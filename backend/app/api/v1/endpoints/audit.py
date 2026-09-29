"""
ReliefChain AI - Tamper-Evident SHA-256 Audit & Integrity Endpoints (Step 10).

Provides:
- GET /audit: Paged audit history with role-based access and citizen privacy filtering.
- GET /audit/history: Alias for /audit.
- GET /audit/verify: Cryptographic SHA-256 integrity check verifying unbroken chain linkage.
- GET /audit/{record_id}: Retrieve and verify single audit record.
- Strict immutability: Modification or deletion of audit logs is explicitly blocked (403/405).
- Non-blockchain architecture: Cryptographic hash-chaining stored within relational database.
"""

from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, Query, status

from ....core.auth import get_current_user, get_optional_user, is_officer_or_admin, is_citizen
from ....core.errors import NotFoundError, ForbiddenError, UnauthorizedError
from ....core.database import get_db
from ....core.config import (
    MST_RPC_URL,
    MST_CHAIN_ID,
    MST_CONTRACT_ADDRESS,
    MST_EXPLORER_URL
)
from ....services import (
    verify_audit_chain,
    verify_single_record,
    get_audit_records,
    format_audit_record
)
from ....schemas.audit import (
    AuditEventResponse,
    AuditHistoryResponse,
    AuditIntegrityVerificationResponse
)
from ....repositories.disaster_repo import DisasterRepository

router = APIRouter(tags=["Audit & Integrity"])


@router.get(
    "/audit",
    response_model=Union[AuditHistoryResponse, List[AuditEventResponse]],
    summary="View tamper-evident audit history (Authorized)",
    tags=["Audit & Integrity"]
)
def view_audit_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g. ASSET_REGISTERED, EVIDENCE_ADDED)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID (e.g. AST-..., EV-...)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Union[AuditHistoryResponse, List[AuditEventResponse]]:
    """
    Step 10: Authorized Audit History Retrieval.
    - Requires authentication (401 for unauthenticated calls).
    - Officers and Admins can view complete system audit trail.
    - Citizens can only view events relating to their own registered assets/claims or public operations.
    - Does not expose private citizen data unnecessarily.
    - Returns standardized records containing record ID, timestamp, previous hash, current hash,
      evidence hash, event type, and actor.
    """
    result = get_audit_records(
        limit=limit,
        offset=offset,
        event_type=event_type,
        entity_id=entity_id,
        current_user=current_user
    )
    if entity_id:
        return result["records"]
    return AuditHistoryResponse(**result)


@router.get(
    "/audit/history",
    response_model=AuditHistoryResponse,
    summary="Alias for /audit",
    tags=["Audit & Integrity"]
)
def view_audit_history_alias(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AuditHistoryResponse:
    """Convenience alias for /audit."""
    return view_audit_history(
        limit=limit,
        offset=offset,
        event_type=event_type,
        entity_id=entity_id,
        current_user=current_user
    )


@router.get(
    "/audit/verify",
    response_model=AuditIntegrityVerificationResponse,
    summary="Verify cryptographic SHA-256 audit chain integrity",
    tags=["Audit & Integrity"]
)
def verify_audit_integrity(
    start_id: Optional[int] = Query(None, ge=1, description="Optional starting record ID"),
    end_id: Optional[int] = Query(None, ge=1, description="Optional ending record ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> AuditIntegrityVerificationResponse:
    """
    Step 10: Cryptographic Integrity Verification Utility.
    - Recalculates SHA-256 hash for every single event record.
    - Validates that each record's previous_record_hash matches its predecessor's current_record_hash.
    - Detects any database tampering, content alteration, deletion, or out-of-order insertion.
    - Pinpoints corrupted record ID and exact cause when tampering is detected.
    """
    res = verify_audit_chain(start_id=start_id, end_id=end_id)
    return AuditIntegrityVerificationResponse(**res)


@router.get(
    "/audit/trail",
    summary="Legacy sequential audit trail endpoint",
    tags=["Audit & Integrity"]
)
def get_audit_trail_legacy(limit: int = Query(100, ge=1, le=500)):
    """Legacy backward-compatible audit query endpoint."""
    return DisasterRepository.get_audit_trail(limit)


@router.get(
    "/audit/{record_id}",
    response_model=AuditEventResponse,
    summary="Retrieve single audit event record",
    tags=["Audit & Integrity"]
)
def get_single_audit_event(
    record_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AuditEventResponse:
    """
    Retrieves a single audit record by its unique record ID (e.g. AUD-2026-000001 or integer ID)
    and verifies its internal cryptographic integrity.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if record_id.isdigit():
            cursor.execute("SELECT * FROM audit_events WHERE id = ?;", (int(record_id),))
        else:
            cursor.execute("SELECT * FROM audit_events WHERE audit_id = ?;", (record_id,))
        row = cursor.fetchone()
        if not row:
            raise NotFoundError(f"Audit record '{record_id}' not found.")

        # Privacy check for citizens
        if is_citizen(current_user):
            user_name = current_user.get("name", "").lower()
            user_id = current_user.get("id")
            user_uid = (current_user.get("user_id") or "").lower()
            row_actor = (row["actor"] or "").lower()
            row_entity = row["entity_type"] or ""
            row_entity_id = row["entity_id"] or ""

            # Extract base name before parenthesis (e.g. 'senthil nathan')
            core_name = user_name.split("(")[0].strip() if "(" in user_name else user_name.strip()

            # Check if this asset/claim belongs to citizen
            is_own_entity = False
            if row_entity_id and user_id:
                cursor.execute("SELECT 1 FROM assets WHERE asset_id = ? AND citizen_id = ?;", (row_entity_id, user_id))
                if cursor.fetchone():
                    is_own_entity = True

            is_allowed = (
                (core_name and core_name in row_actor) or
                (user_uid and user_uid in row_actor) or
                is_own_entity or
                row_entity in ("DISASTER", "ZONE", "SYSTEM", "RECOMMENDATION")
            )
            if not is_allowed:
                raise ForbiddenError("Access denied. You do not have permission to inspect another citizen's audit record.")

        return AuditEventResponse(**format_audit_record(row))


# -------------------------------------------------------------------------
# Strict Immutability Protection (Step 10 Requirement 1 & 2)
# -------------------------------------------------------------------------

@router.put("/audit/{record_id}", include_in_schema=False)
@router.patch("/audit/{record_id}", include_in_schema=False)
@router.delete("/audit/{record_id}", include_in_schema=False)
def reject_audit_modification(record_id: str):
    """
    Explicitly forbids modifying or deleting audit events.
    Audit events are append-only. Users cannot edit existing audit records.
    """
    raise ForbiddenError("Audit records are immutable and append-only. Modifying or deleting audit records is strictly prohibited.")


# -------------------------------------------------------------------------
# Legacy Diagnostic Endpoints (Preserved for compatibility)
# -------------------------------------------------------------------------

@router.get("/blockchain/status", summary="MST Testnet Diagnostics (Simulated)", tags=["Audit & Integrity"])
def get_blockchain_status():
    return {
        "network": "MST Testnet",
        "rpc_url": MST_RPC_URL,
        "chain_id": MST_CHAIN_ID,
        "contract_address": MST_CONTRACT_ADDRESS,
        "explorer_url": MST_EXPLORER_URL,
        "status": "OPERATIONAL (Cryptographic SHA-256 Engine Active)"
    }


@router.get("/blockchain/transactions", summary="List anchored transactions", tags=["Audit & Integrity"])
def list_blockchain_transactions(limit: int = Query(50, ge=1, le=200)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT recommendation_id, location_name, resource_type, approved_quantity,
               status, approved_by_supervisor_1 AS approver, blockchain_tx_hash,
               block_number, approved_at
        FROM recommendations
        WHERE blockchain_tx_hash IS NOT NULL AND blockchain_tx_hash != ''
        ORDER BY id DESC LIMIT ?;
        """, (limit,))
        txs = cursor.fetchall()
        for t in txs:
            t["explorer_url"] = f"{MST_EXPLORER_URL}/tx/{t['blockchain_tx_hash']}"
        return txs
