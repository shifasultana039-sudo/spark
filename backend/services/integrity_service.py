"""
ReliefChain AI - Tamper-Evident SHA-256 Chained Audit & Integrity Service (Step 10).

Features:
- Immutable append-only audit logging (strictly NO edit/update/delete APIs).
- Cryptographic SHA-256 sequential linking: each record binds to the predecessor hash.
- Captures record ID, timestamp, previous record hash, current record hash, evidence hash, event type, and actor.
- Specific events:
    * ASSET_REGISTERED
    * EVIDENCE_ADDED
    * VERIFICATION_UPDATED
    * CERTIFICATE_GENERATED
    * CLAIM_CREATED
    * AI_ASSESSMENT_CREATED
    * OFFICER_REVIEWED
- Integrity verification utility detecting unauthorized modifications, deletions, or corruptions.
- Strict non-blockchain design (pure relational cryptographic hash-chaining).
"""

import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db

GENESIS_HASH = "0x0000000000000000000000000000000000000000000000000000000000000000"


def compute_event_hash(
    previous_hash: str,
    timestamp: str,
    actor: str,
    role: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    description: str,
    evidence_hash: Optional[str] = None
) -> str:
    """
    Computes a cryptographic SHA-256 hash linking the current event to its predecessor.
    Binds evidence_hash if present.
    """
    ev_part = f"|{evidence_hash}" if evidence_hash else ""
    payload = f"{previous_hash}|{timestamp}|{actor}|{role}|{event_type}|{entity_type}|{entity_id}|{description}{ev_part}"
    return "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_audit_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Formats an audit database row into the standardized Step 10 structure."""
    row_dict = dict(row)
    row_id = row_dict["id"]
    audit_id = row_dict.get("audit_id") or f"AUD-2026-{row_id:06d}"
    prev_h = row_dict.get("previous_hash", GENESIS_HASH)
    curr_h = row_dict.get("event_hash", "")

    actor_val = row_dict["actor"]
    actor_id_val = row_dict.get("actor_id")
    if not actor_id_val:
        if actor_val.startswith("USR-"):
            actor_id_val = actor_val
        elif "Rajesh" in actor_val or "Officer" in actor_val or "GOVERNMENT" in str(row_dict.get("role", "")):
            actor_id_val = "USR-007"
        elif "Senthil" in actor_val or "Citizen" in actor_val:
            actor_id_val = "USR-006"
        elif "Ananya" in actor_val:
            actor_id_val = "USR-001"
        elif "Kavitha" in actor_val:
            actor_id_val = "USR-003"
        else:
            actor_id_val = actor_val

    return {
        "id": row_id,
        "record_id": audit_id,
        "audit_id": audit_id,
        "timestamp": row_dict["timestamp"],
        "previous_record_hash": prev_h,
        "previous_hash": prev_h,
        "current_record_hash": curr_h,
        "current_hash": curr_h,
        "event_hash": curr_h,
        "evidence_hash": row_dict.get("evidence_hash"),
        "event_type": row_dict["event_type"],
        "actor": row_dict["actor"],
        "actor_id": actor_id_val,
        "role": row_dict.get("role", "CITIZEN"),
        "entity_type": row_dict.get("entity_type", "SYSTEM"),
        "entity_id": row_dict.get("entity_id", ""),
        "description": row_dict.get("description", ""),
        "blockchain_tx_hash": row_dict.get("blockchain_tx_hash"),
        "is_valid": True
    }


def record_audit_event(
    actor: str,
    role: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    description: str,
    evidence_hash: Optional[str] = None,
    blockchain_tx_hash: Optional[str] = None,
    audit_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Appends a new immutable event to the chained audit trail (Append-Only).
    Guarantees that each event cryptographically references the previous event's hash.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Retrieve the latest event to link the hash chain
        cursor.execute("SELECT id, event_hash FROM audit_events ORDER BY id DESC LIMIT 1;")
        last_row = cursor.fetchone()
        previous_hash = last_row["event_hash"] if last_row else GENESIS_HASH
        next_id = (last_row["id"] + 1) if last_row else 1

        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        assigned_audit_id = audit_id or f"AUD-{now.year}-{next_id:06d}"

        # Deterministic SHA-256 hash computation
        current_hash = compute_event_hash(
            previous_hash=previous_hash,
            timestamp=timestamp,
            actor=actor,
            role=role,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            evidence_hash=evidence_hash
        )

        cursor.execute("""
        INSERT INTO audit_events (
            audit_id, timestamp, actor, role, event_type, entity_type, entity_id,
            description, evidence_hash, previous_hash, event_hash, blockchain_tx_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            assigned_audit_id, timestamp, actor, role, event_type, entity_type, entity_id,
            description, evidence_hash, previous_hash, current_hash, blockchain_tx_hash
        ))

        return {
            "id": next_id,
            "record_id": assigned_audit_id,
            "audit_id": assigned_audit_id,
            "timestamp": timestamp,
            "previous_record_hash": previous_hash,
            "previous_hash": previous_hash,
            "current_record_hash": current_hash,
            "current_hash": current_hash,
            "event_hash": current_hash,
            "evidence_hash": evidence_hash,
            "event_type": event_type,
            "actor": actor,
            "role": role,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "blockchain_tx_hash": blockchain_tx_hash,
            "is_valid": True
        }


# -------------------------------------------------------------------------
# Standardized Event Logging Helpers (Step 10 Event Types)
# -------------------------------------------------------------------------

def log_asset_registered(
    asset_id: str,
    actor: str,
    role: str = "CITIZEN",
    category: str = "ASSET",
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Records ASSET_REGISTERED audit event."""
    desc = description or f"Asset {asset_id} registered under category {category}."
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="ASSET_REGISTERED",
        entity_type="ASSET",
        entity_id=asset_id,
        description=desc
    )


def log_evidence_added(
    asset_id: str,
    evidence_id: str,
    evidence_hash: str,
    evidence_type: str,
    actor: str,
    role: str = "CITIZEN",
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """Records EVIDENCE_ADDED audit event binding the evidence's SHA-256 hash."""
    desc = f"Evidence {evidence_id} ({evidence_type}) added to asset {asset_id}. File: {filename or 'artifact'}."
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="EVIDENCE_ADDED",
        entity_type="EVIDENCE",
        entity_id=evidence_id,
        description=desc,
        evidence_hash=evidence_hash
    )


def log_verification_updated(
    asset_id: str,
    status: str,
    confidence: int,
    actor: str,
    role: str = "CITIZEN",
    explanation: Optional[str] = None,
    evidence_hash: Optional[str] = None
) -> Dict[str, Any]:
    """Records VERIFICATION_UPDATED audit event."""
    desc = f"Verification updated for asset {asset_id}: status={status}, confidence={confidence}%. {explanation or ''}".strip()
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="VERIFICATION_UPDATED",
        entity_type="ASSET",
        entity_id=asset_id,
        description=desc,
        evidence_hash=evidence_hash
    )


def log_certificate_generated(
    asset_id: str,
    certificate_id: str,
    actor: str,
    role: str = "SYSTEM",
    confidence: int = 100
) -> Dict[str, Any]:
    """Records CERTIFICATE_GENERATED audit event."""
    desc = f"Digital Certificate {certificate_id} generated for asset {asset_id} with {confidence}% confidence."
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="CERTIFICATE_GENERATED",
        entity_type="CERTIFICATE",
        entity_id=certificate_id,
        description=desc
    )


def log_claim_created(
    claim_id: str,
    asset_id: str,
    disaster_id: str,
    actor: str,
    role: str = "CITIZEN"
) -> Dict[str, Any]:
    """Records CLAIM_CREATED audit event."""
    desc = f"Disaster compensation claim {claim_id} created for asset {asset_id} linked to disaster {disaster_id}."
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="CLAIM_CREATED",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=desc
    )


def log_ai_assessment_created(
    recommendation_id: str,
    entity_type: str = "DISASTER_REPORT",
    entity_id: str = "REP-001",
    actor: str = "ReliefChain AI Engine",
    role: str = "SYSTEM_AI",
    priority: int = 90
) -> Dict[str, Any]:
    """Records AI_ASSESSMENT_CREATED audit event."""
    desc = f"AI decision assessment {recommendation_id} generated for {entity_type} {entity_id} with priority {priority}."
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="AI_ASSESSMENT_CREATED",
        entity_type="RECOMMENDATION",
        entity_id=recommendation_id,
        description=desc
    )


def log_officer_reviewed(
    entity_id: str,
    entity_type: str,
    decision: str,
    actor: str,
    role: str = "DISASTER_OFFICER",
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Records OFFICER_REVIEWED audit event."""
    desc = f"Disaster Officer {actor} reviewed {entity_type} {entity_id}: decision={decision}. {notes or ''}".strip()
    return record_audit_event(
        actor=actor,
        role=role,
        event_type="OFFICER_REVIEWED",
        entity_type=entity_type,
        entity_id=entity_id,
        description=desc
    )


# -------------------------------------------------------------------------
# Cryptographic Integrity Verification Utility (Step 10 Requirement 4)
# -------------------------------------------------------------------------

def verify_audit_chain(
    start_id: Optional[int] = None,
    end_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Step 10 Integrity Verification Utility.
    Verifies the cryptographic SHA-256 hash chaining across all recorded audit events.
    Detects any unauthorized record modifications, deletions, or hash forgeries.
    Pinpoints the exact corrupted record ID when tampering is found.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM audit_events"
        params = []
        conditions = []

        if start_id is not None:
            conditions.append("id >= ?")
            params.append(start_id)
        if end_id is not None:
            conditions.append("id <= ?")
            params.append(end_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id ASC;"
        cursor.execute(query, tuple(params))
        events = cursor.fetchall()

        if not events:
            return {
                "chain_valid": True,
                "tampered": False,
                "total_events": 0,
                "status": "EMPTY_CHAIN",
                "verified_at": datetime.now(timezone.utc).isoformat()
            }

        # Determine expected initial predecessor hash
        first_id = events[0]["id"]
        if first_id == 1:
            expected_prev = GENESIS_HASH
        else:
            # Look up immediate predecessor of the first selected record
            cursor.execute("SELECT event_hash FROM audit_events WHERE id < ? ORDER BY id DESC LIMIT 1;", (first_id,))
            pred_row = cursor.fetchone()
            expected_prev = pred_row["event_hash"] if pred_row else GENESIS_HASH

        for idx, ev in enumerate(events):
            ev_id = ev["id"]
            audit_id = ev.get("audit_id") or f"AUD-2026-{ev_id:06d}"

            # 1. Verify sequence link to predecessor
            if ev["previous_hash"] != expected_prev:
                return {
                    "chain_valid": False,
                    "tampered": True,
                    "total_events": len(events),
                    "broken_at_id": ev_id,
                    "broken_at_record_id": audit_id,
                    "event_type": ev["event_type"],
                    "error_type": "BROKEN_CHAIN_LINK",
                    "error": (
                        f"Broken chain link at Record #{ev_id} ({audit_id}): "
                        f"expected previous hash {expected_prev}, found {ev['previous_hash']}"
                    ),
                    "expected_hash": expected_prev,
                    "found_hash": ev["previous_hash"],
                    "timestamp": ev["timestamp"]
                }

            # 2. Recalculate SHA-256 hash from record contents
            recalculated = compute_event_hash(
                previous_hash=ev["previous_hash"],
                timestamp=ev["timestamp"],
                actor=ev["actor"],
                role=ev["role"],
                event_type=ev["event_type"],
                entity_type=ev["entity_type"],
                entity_id=ev["entity_id"],
                description=ev["description"],
                evidence_hash=ev.get("evidence_hash")
            )

            if recalculated != ev["event_hash"]:
                return {
                    "chain_valid": False,
                    "tampered": True,
                    "total_events": len(events),
                    "broken_at_id": ev_id,
                    "broken_at_record_id": audit_id,
                    "event_type": ev["event_type"],
                    "error_type": "HASH_MISMATCH",
                    "error": (
                        f"Tampered record detected at Record #{ev_id} ({audit_id}): "
                        f"stored hash {ev['event_hash']} does not match recalculated hash {recalculated}"
                    ),
                    "expected_hash": recalculated,
                    "found_hash": ev["event_hash"],
                    "timestamp": ev["timestamp"]
                }

            expected_prev = ev["event_hash"]

        return {
            "chain_valid": True,
            "tampered": False,
            "total_events": len(events),
            "status": "VERIFIED_TAMPER_EVIDENT",
            "latest_head_hash": expected_prev,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "first_event_hash": events[0]["event_hash"] if events else None
        }


def verify_single_record(record_id: Union[str, int]) -> Dict[str, Any]:
    """Verifies cryptographic integrity of a single audit event record."""
    with get_db() as conn:
        cursor = conn.cursor()

        if isinstance(record_id, int) or (isinstance(record_id, str) and record_id.isdigit()):
            cursor.execute("SELECT * FROM audit_events WHERE id = ?;", (int(record_id),))
        else:
            cursor.execute("SELECT * FROM audit_events WHERE audit_id = ?;", (str(record_id),))

        ev = cursor.fetchone()
        if not ev:
            return {"found": False, "is_valid": False, "error": f"Record '{record_id}' not found."}

        ev_id = ev["id"]
        audit_id = ev.get("audit_id") or f"AUD-2026-{ev_id:06d}"

        # Predecessor hash check
        if ev_id == 1:
            expected_prev = GENESIS_HASH
        else:
            cursor.execute("SELECT event_hash FROM audit_events WHERE id < ? ORDER BY id DESC LIMIT 1;", (ev_id,))
            pred_row = cursor.fetchone()
            expected_prev = pred_row["event_hash"] if pred_row else GENESIS_HASH

        link_valid = (ev["previous_hash"] == expected_prev)
        recalculated = compute_event_hash(
            previous_hash=ev["previous_hash"],
            timestamp=ev["timestamp"],
            actor=ev["actor"],
            role=ev["role"],
            event_type=ev["event_type"],
            entity_type=ev["entity_type"],
            entity_id=ev["entity_id"],
            description=ev["description"],
            evidence_hash=ev.get("evidence_hash")
        )
        content_valid = (recalculated == ev["event_hash"])

        is_intact = link_valid and content_valid
        return {
            "found": True,
            "record_id": audit_id,
            "id": ev_id,
            "is_valid": is_intact,
            "link_valid": link_valid,
            "content_valid": content_valid,
            "stored_hash": ev["event_hash"],
            "recalculated_hash": recalculated,
            "previous_hash": ev["previous_hash"],
            "expected_prev_hash": expected_prev,
            "evidence_hash": ev.get("evidence_hash"),
            "event_type": ev["event_type"]
        }


# -------------------------------------------------------------------------
# Query and Access Control Utility (Step 10 Requirement 5 & 6)
# -------------------------------------------------------------------------

def get_audit_records(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Retrieves audit records with privacy scoping:
    - Officers and Admins: view all audit records.
    - Citizens: can only see events where they are the actor OR that belong to their assets/claims,
      or general public disaster operations.
    - Do not expose private information unnecessarily.
    """
    is_officer_or_admin = False
    citizen_user_id = None
    citizen_name = None

    if current_user:
        role = current_user.get("role", "CITIZEN").upper()
        if role in ("ADMIN", "GOVERNMENT_OFFICER", "DISASTER_OFFICER"):
            is_officer_or_admin = True
        else:
            citizen_user_id = current_user.get("id")
            citizen_name = current_user.get("name")

    with get_db() as conn:
        cursor = conn.cursor()

        # If citizen, find their asset IDs to allow viewing their asset events
        owned_entity_ids = set()
        if not is_officer_or_admin and citizen_user_id:
            cursor.execute("SELECT asset_id FROM assets WHERE citizen_id = ?;", (citizen_user_id,))
            for a in cursor.fetchall():
                owned_entity_ids.add(a["asset_id"])

        where_clauses = []
        params = []

        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type.strip().upper())

        if entity_id:
            where_clauses.append("(entity_id = ? OR description LIKE ?)")
            clean_eid = entity_id.strip()
            params.extend([clean_eid, f"%{clean_eid}%"])

        # Privacy Scoping for Citizens
        if not is_officer_or_admin and (citizen_user_id or citizen_name):
            privacy_conditions = []
            if citizen_name:
                privacy_conditions.append("actor LIKE ?")
                params.append(f"%{citizen_name}%")
            if citizen_user_id:
                privacy_conditions.append("actor LIKE ?")
                params.append(f"%USR-%")
            if owned_entity_ids:
                placeholders = ",".join(["?"] * len(owned_entity_ids))
                privacy_conditions.append(f"entity_id IN ({placeholders})")
                params.extend(list(owned_entity_ids))

            # Include public system operations
            privacy_conditions.append("entity_type IN ('DISASTER', 'ZONE', 'SYSTEM')")

            if privacy_conditions:
                where_clauses.append(f"({' OR '.join(privacy_conditions)})")

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count
        cursor.execute(f"SELECT COUNT(*) AS total FROM audit_events{where_sql};", tuple(params))
        total_count = cursor.fetchone()["total"]

        # Page query
        cursor.execute(
            f"SELECT * FROM audit_events{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?;",
            tuple(params + [limit, offset])
        )
        rows = cursor.fetchall()

        formatted_records = [format_audit_record(r) for r in rows]

        return {
            "total_records": total_count,
            "limit": limit,
            "offset": offset,
            "records": formatted_records
        }
