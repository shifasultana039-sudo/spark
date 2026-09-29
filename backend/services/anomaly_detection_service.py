"""
ReliefChain AI — Deterministic Anomaly Detection Service (Step 16).

Scans claims for structural discrepancies using purely rule-based, deterministic signals.

IMPORTANT DESIGN PRINCIPLES
────────────────────────────
• Citizens are NEVER labelled as fraudulent.
• Every flag uses the neutral status  REVIEW_REQUIRED.
• All confidence values are expressed as integer percentages (0-100).
• Results are persisted in the  anomaly_flags  table so officers can audit them.

Supported anomaly signal types
───────────────────────────────
1.  DUPLICATE_ASSET_REGISTRATION   — same integrity_hash registered under two assets
2.  REUSED_EVIDENCE_HASH           — same SHA-256 evidence file appears in another claim / asset
3.  REPEATED_SUBMISSION            — same household files multiple claims for the same asset & disaster
4.  LOCATION_CONFLICT              — claim evidence GPS differs significantly from asset registered location
5.  MODIFIED_EVIDENCE              — stored file hash no longer matches the originally recorded hash
6.  MULTIPLE_CLAIMS_SAME_ASSET     — more than one active claim for the same asset regardless of disaster
7.  METADATA_CONFLICT              — evidence captured_timestamp is before the disaster was declared

Public surface
──────────────
run_anomaly_detection(claim_id)  →  List[Dict]   (all anomalies found for the claim)
check_evidence_anomalies(...)    →  Optional[Dict] (single evidence hash check, backward-compat)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns the great-circle distance in kilometres between two GPS points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _persist_anomaly(
    entity_type: str,
    entity_id: str,
    flag_type: str,
    reason: str,
    similarity_score: int = 100,
    related_record: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inserts a single anomaly flag into the anomaly_flags table and returns
    a normalised dict matching the AnomalyResponse schema.
    Skips persistence if an identical (entity_id + flag_type + reason) row
    already exists to avoid duplicate flags on repeated scans.
    """
    now = _now_iso()
    with get_db() as conn:
        cursor = conn.cursor()

        # Idempotency guard
        cursor.execute(
            """
            SELECT id FROM anomaly_flags
            WHERE entity_id = ? AND flag_type = ? AND reason = ?
            LIMIT 1;
            """,
            (entity_id, flag_type, reason),
        )
        existing = cursor.fetchone()
        if existing:
            # Return the already-stored row
            cursor.execute(
                "SELECT * FROM anomaly_flags WHERE id = ?;", (existing["id"],)
            )
            row = cursor.fetchone()
            return _row_to_dict(row, related_record)

        cursor.execute(
            """
            INSERT INTO anomaly_flags
                (entity_type, entity_id, flag_type, similarity_score, status, reason, created_at)
            VALUES (?, ?, ?, ?, 'REVIEW_REQUIRED', ?, ?);
            """,
            (entity_type, entity_id, flag_type, similarity_score, reason, now),
        )
        row_id = cursor.lastrowid
        cursor.execute("SELECT * FROM anomaly_flags WHERE id = ?;", (row_id,))
        row = cursor.fetchone()
    return _row_to_dict(row, related_record)


def _row_to_dict(row: Any, related_record: Optional[str] = None) -> Dict[str, Any]:
    """Converts a sqlite3 Row (or dict) to a clean anomaly dict with Step 16 fields."""
    d = dict(row)
    d["review_status"] = "REVIEW_REQUIRED"
    d["status"] = "REVIEW_REQUIRED"
    d["related_record"] = related_record or d.get("related_record")
    d["type"] = d.get("flag_type")
    d["similarity"] = d.get("similarity_score")
    d["confidence"] = d.get("similarity_score")
    d["created_timestamp"] = d.get("created_at")
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Signal detectors  (each returns a list of anomaly dicts, possibly empty)
# ──────────────────────────────────────────────────────────────────────────────

def _detect_duplicate_asset_registration(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 1 — DUPLICATE_ASSET_REGISTRATION
    Checks if the asset referenced by the claim has the same integrity_hash
    as any other asset in the registry.
    """
    asset_id = claim.get("asset_id", "")
    claim_id = claim.get("claim_id", "")
    flags: List[Dict[str, Any]] = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT integrity_hash FROM assets WHERE asset_id = ?;", (asset_id,)
        )
        row = cursor.fetchone()
        if not row or not row["integrity_hash"]:
            return flags

        integrity_hash = row["integrity_hash"]
        cursor.execute(
            """
            SELECT asset_id, household_ref
            FROM assets
            WHERE integrity_hash = ? AND asset_id != ?;
            """,
            (integrity_hash, asset_id),
        )
        duplicates = cursor.fetchall()

    for dup in duplicates:
        reason = (
            f"Asset '{asset_id}' shares an identical integrity hash with asset "
            f"'{dup['asset_id']}' (household {dup['household_ref']}). "
            f"Officer verification required to confirm distinct physical ownership."
        )
        flags.append(
            _persist_anomaly(
                entity_type="CLAIM",
                entity_id=claim_id,
                flag_type="DUPLICATE_ASSET_REGISTRATION",
                reason=reason,
                similarity_score=100,
                related_record=dup["asset_id"],
            )
        )
    return flags


def _detect_reused_evidence_hash(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 2 — REUSED_EVIDENCE_HASH
    Checks whether any claim evidence file hash appears in other claims or asset evidence.
    """
    claim_id = claim.get("claim_id", "")
    flags: List[Dict[str, Any]] = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT evidence_id, sha256_hash, original_filename FROM claim_evidence WHERE claim_id = ?;",
            (claim_id,),
        )
        evidence_rows = cursor.fetchall()

        for ev in evidence_rows:
            sha = ev["sha256_hash"]
            # Check other claims
            cursor.execute(
                """
                SELECT ce.claim_id, ce.original_filename
                FROM claim_evidence ce
                WHERE ce.sha256_hash = ? AND ce.claim_id != ?
                LIMIT 5;
                """,
                (sha, claim_id),
            )
            other_claims = cursor.fetchall()
            for oc in other_claims:
                reason = (
                    f"Evidence file '{ev['original_filename']}' has an identical SHA-256 hash "
                    f"to a file submitted in claim '{oc['claim_id']}'. "
                    f"Field inspection recommended to confirm distinct post-disaster evidence."
                )
                flags.append(
                    _persist_anomaly(
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        flag_type="REUSED_EVIDENCE_HASH",
                        reason=reason,
                        similarity_score=100,
                        related_record=oc["claim_id"],
                    )
                )

            # Check asset evidence
            cursor.execute(
                """
                SELECT ae.asset_id, ae.original_filename, a.household_ref
                FROM asset_evidence ae
                JOIN assets a ON ae.asset_id = a.asset_id
                WHERE ae.sha256_hash = ?
                LIMIT 5;
                """,
                (sha,),
            )
            asset_matches = cursor.fetchall()
            for am in asset_matches:
                reason = (
                    f"Evidence image '{ev['original_filename']}' appears similar to evidence "
                    f"submitted in another claim (asset '{am['asset_id']}', "
                    f"household {am['household_ref']}). "
                    f"Officer verification required."
                )
                flags.append(
                    _persist_anomaly(
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        flag_type="REUSED_EVIDENCE_HASH",
                        reason=reason,
                        similarity_score=96,
                        related_record=am["asset_id"],
                    )
                )
    return flags


def _detect_repeated_submission(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 3 — REPEATED_SUBMISSION
    Flags when the same household submits more than one claim for the same
    asset under the same disaster event.
    """
    claim_id = claim.get("claim_id", "")
    asset_id = claim.get("asset_id", "")
    household_ref = claim.get("household_ref", "")
    disaster_id = claim.get("disaster_id", "")
    flags: List[Dict[str, Any]] = []

    if not (asset_id and household_ref and disaster_id):
        return flags

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT claim_id, created_at
            FROM disaster_claims
            WHERE asset_id = ? AND household_ref = ? AND disaster_id = ? AND claim_id != ?;
            """,
            (asset_id, household_ref, disaster_id, claim_id),
        )
        others = cursor.fetchall()

    for oth in others:
        reason = (
            f"Household '{household_ref}' has submitted multiple claims "
            f"(including '{oth['claim_id']}') for asset '{asset_id}' "
            f"under disaster '{disaster_id}'. "
            f"Officer review required to confirm distinct damage events."
        )
        flags.append(
            _persist_anomaly(
                entity_type="CLAIM",
                entity_id=claim_id,
                flag_type="REPEATED_SUBMISSION",
                reason=reason,
                similarity_score=100,
                related_record=oth["claim_id"],
            )
        )
    return flags


def _detect_location_conflict(claim: Dict[str, Any], distance_threshold_km: float = 50.0) -> List[Dict[str, Any]]:
    """
    Signal 4 — LOCATION_CONFLICT
    Compares GPS coordinates embedded in claim evidence against the asset's
    registered location. Flags when the discrepancy exceeds the threshold.
    """
    claim_id = claim.get("claim_id", "")
    asset_id = claim.get("asset_id", "")
    flags: List[Dict[str, Any]] = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT latitude, longitude, location_address FROM assets WHERE asset_id = ?;",
            (asset_id,),
        )
        asset_row = cursor.fetchone()
        if not asset_row:
            return flags

        asset_lat = asset_row["latitude"]
        asset_lon = asset_row["longitude"]
        if asset_lat is None or asset_lon is None:
            return flags

        cursor.execute(
            """
            SELECT evidence_id, latitude, longitude, original_filename
            FROM claim_evidence
            WHERE claim_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL;
            """,
            (claim_id,),
        )
        evidence_with_gps = cursor.fetchall()

    for ev in evidence_with_gps:
        ev_lat = ev["latitude"]
        ev_lon = ev["longitude"]
        if ev_lat is None or ev_lon is None:
            continue
        dist_km = _haversine_km(asset_lat, asset_lon, ev_lat, ev_lon)
        if dist_km > distance_threshold_km:
            confidence = min(100, int(dist_km / distance_threshold_km * 50))
            reason = (
                f"Evidence '{ev['original_filename']}' (evidence_id: {ev['evidence_id']}) "
                f"was captured approximately {dist_km:.1f} km from the asset's registered "
                f"location ({asset_row['location_address']}). "
                f"Officer site verification recommended."
            )
            flags.append(
                _persist_anomaly(
                    entity_type="CLAIM",
                    entity_id=claim_id,
                    flag_type="LOCATION_CONFLICT",
                    reason=reason,
                    similarity_score=confidence,
                    related_record=ev["evidence_id"],
                )
            )
    return flags


def _detect_modified_evidence(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 5 — MODIFIED_EVIDENCE
    Compares the sha256_hash stored at evidence upload time against what the
    storage provider currently reports for the same file. A mismatch means
    the stored file may have been altered after upload.

    NOTE: This check is best-effort; if the storage provider cannot locate
    the physical file it is silently skipped (no false positives).
    """
    claim_id = claim.get("claim_id", "")
    flags: List[Dict[str, Any]] = []

    try:
        try:
            from storage.provider import storage_provider
        except (ImportError, ValueError):
            from app.storage.provider import storage_provider
    except Exception:
        return flags  # Storage unavailable — skip gracefully

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT evidence_id, sha256_hash, original_filename FROM claim_evidence WHERE claim_id = ?;",
            (claim_id,),
        )
        evidence_rows = cursor.fetchall()

    for ev in evidence_rows:
        evidence_id = ev["evidence_id"]
        recorded_hash = ev["sha256_hash"]
        original_filename = ev.get("original_filename", "")
        custom_key = f"{evidence_id}_{original_filename}"

        try:
            current_hash = storage_provider.get_file_hash(custom_key, is_private=True)
        except Exception:
            current_hash = None

        clean_recorded = recorded_hash.replace("0x", "").lower().strip() if recorded_hash else ""
        clean_current = current_hash.replace("0x", "").lower().strip() if current_hash else ""

        if clean_current and clean_recorded and clean_current != clean_recorded:
            reason = (
                f"Evidence file '{original_filename}' (evidence_id: {evidence_id}) "
                f"has a SHA-256 hash that differs from the value recorded at upload time. "
                f"The file may have been modified after submission. "
                f"Officer verification required."
            )
            flags.append(
                _persist_anomaly(
                    entity_type="CLAIM",
                    entity_id=claim_id,
                    flag_type="MODIFIED_EVIDENCE",
                    reason=reason,
                    similarity_score=0,
                    related_record=evidence_id,
                )
            )
    return flags


def _detect_multiple_claims_same_asset(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 6 — MULTIPLE_CLAIMS_SAME_ASSET
    Flags when more than one claim references the same asset_id (regardless of
    disaster event or household).
    """
    claim_id = claim.get("claim_id", "")
    asset_id = claim.get("asset_id", "")
    flags: List[Dict[str, Any]] = []

    if not asset_id:
        return flags

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT claim_id, disaster_id, review_status, created_at
            FROM disaster_claims
            WHERE asset_id = ? AND claim_id != ?
            ORDER BY created_at DESC;
            """,
            (asset_id, claim_id),
        )
        others = cursor.fetchall()

    # Only flag when 1+ other active (non-rejected) claims exist
    active_others = [o for o in others if o.get("review_status", "") not in ("REJECTED", "DISMISSED")]
    for oth in active_others:
        reason = (
            f"Asset '{asset_id}' is referenced in another active claim "
            f"'{oth['claim_id']}' (status: {oth['review_status']}, "
            f"disaster: {oth['disaster_id']}). "
            f"Officer review required to confirm this represents a distinct, compensable loss."
        )
        flags.append(
            _persist_anomaly(
                entity_type="CLAIM",
                entity_id=claim_id,
                flag_type="MULTIPLE_CLAIMS_SAME_ASSET",
                reason=reason,
                similarity_score=100,
                related_record=oth["claim_id"],
            )
        )
    return flags


def _detect_metadata_conflict(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Signal 7 — METADATA_CONFLICT
    Flags evidence whose captured_timestamp pre-dates the declared disaster event,
    which would indicate the evidence could not have documented post-disaster damage.
    """
    claim_id = claim.get("claim_id", "")
    disaster_id = claim.get("disaster_id", "")
    flags: List[Dict[str, Any]] = []

    with get_db() as conn:
        cursor = conn.cursor()

        # Try to fetch disaster declared_at timestamp
        disaster_declared_at: Optional[str] = None
        try:
            cursor.execute(
                "SELECT declared_at FROM disasters WHERE disaster_code = ?;",
                (disaster_id,),
            )
            dis_row = cursor.fetchone()
            if dis_row:
                disaster_declared_at = dis_row["declared_at"]
        except Exception:
            pass

        if not disaster_declared_at:
            return flags

        cursor.execute(
            """
            SELECT evidence_id, captured_timestamp, original_filename
            FROM claim_evidence
            WHERE claim_id = ? AND captured_timestamp IS NOT NULL;
            """,
            (claim_id,),
        )
        evidence_rows = cursor.fetchall()

    for ev in evidence_rows:
        captured_ts = ev.get("captured_timestamp", "")
        if not captured_ts:
            continue
        try:
            # Compare only the date portions to avoid tz edge cases
            captured_date = captured_ts[:10]
            declared_date = disaster_declared_at[:10]
            if captured_date < declared_date:
                reason = (
                    f"Evidence '{ev['original_filename']}' (evidence_id: {ev['evidence_id']}) "
                    f"has a captured timestamp of {captured_ts}, which is before the declared "
                    f"disaster date ({disaster_declared_at}). "
                    f"Evidence predating the disaster cannot document post-disaster damage. "
                    f"Officer verification required."
                )
                flags.append(
                    _persist_anomaly(
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        flag_type="METADATA_CONFLICT",
                        reason=reason,
                        similarity_score=100,
                        related_record=ev["evidence_id"],
                    )
                )
        except Exception:
            continue
    return flags


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def run_anomaly_detection(claim_id: str) -> List[Dict[str, Any]]:
    """
    Runs all seven deterministic anomaly detectors against the given claim.

    Each detector is independent; failures in one detector do not abort the others.

    Returns
    -------
    List[Dict]
        All anomaly flags generated or previously persisted for this claim.
        Empty list if no anomalies are found.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*,
                   a.citizen_id,
                   a.category AS asset_category,
                   a.description AS asset_description,
                   a.latitude AS asset_latitude,
                   a.longitude AS asset_longitude,
                   a.location_address
            FROM disaster_claims c
            LEFT JOIN assets a ON c.asset_id = a.asset_id
            WHERE c.claim_id = ?;
            """,
            (claim_id,),
        )
        row = cursor.fetchone()

    if not row:
        return []

    claim = dict(row)
    all_flags: List[Dict[str, Any]] = []

    detectors = [
        _detect_duplicate_asset_registration,
        _detect_reused_evidence_hash,
        _detect_repeated_submission,
        _detect_location_conflict,
        _detect_modified_evidence,
        _detect_multiple_claims_same_asset,
        _detect_metadata_conflict,
    ]

    for detector in detectors:
        try:
            flags = detector(claim)
            all_flags.extend(flags)
        except Exception:
            # Never let a single detector crash the whole scan
            continue

    return all_flags


def get_persisted_anomalies(claim_id: str) -> List[Dict[str, Any]]:
    """
    Returns all previously persisted anomaly flags for the given claim_id
    without re-running detection. Used for read-only GET requests.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM anomaly_flags
            WHERE entity_id = ? AND entity_type = 'CLAIM'
            ORDER BY id ASC;
            """,
            (claim_id,),
        )
        rows = cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Backward-compatible single-evidence check (used by evidence upload endpoints)
# ──────────────────────────────────────────────────────────────────────────────

def check_evidence_anomalies(
    new_sha256: str,
    current_asset_id: str = None,
    current_claim_id: str = None,
) -> Optional[Dict[str, Any]]:
    """
    Scans existing evidence files for matching hashes across other assets or claims.
    If detected, returns a  REVIEW_REQUIRED  flag rather than any accusation.

    This function is intentionally kept backward-compatible with the signature used
    by the evidence upload endpoints introduced in earlier steps.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check asset evidence
        cursor.execute(
            """
            SELECT ae.asset_id, ae.original_filename, a.household_ref
            FROM asset_evidence ae
            JOIN assets a ON ae.asset_id = a.asset_id
            WHERE ae.sha256_hash = ? AND ae.asset_id != ?;
            """,
            (new_sha256, current_asset_id or ""),
        )
        matched_asset = cursor.fetchone()

        if matched_asset:
            now_str = _now_iso()
            return {
                "flag_type": "REUSED_EVIDENCE_HASH",
                "type": "REUSED_EVIDENCE_HASH",
                "similarity_score": 100,
                "similarity": 100,
                "confidence": 100,
                "status": "REVIEW_REQUIRED",
                "review_status": "REVIEW_REQUIRED",
                "reason": (
                    f"Evidence media hash matches an existing document registered under Asset "
                    f"'{matched_asset['asset_id']}' (Household {matched_asset['household_ref']}). "
                    f"Officer verification required to ensure distinct physical ownership."
                ),
                "related_record": matched_asset["asset_id"],
                "created_at": now_str,
                "created_timestamp": now_str,
            }

        # Check claim evidence
        cursor.execute(
            """
            SELECT ce.claim_id, ce.original_filename, c.household_ref
            FROM claim_evidence ce
            JOIN disaster_claims c ON ce.claim_id = c.claim_id
            WHERE ce.sha256_hash = ? AND ce.claim_id != ?;
            """,
            (new_sha256, current_claim_id or ""),
        )
        matched_claim = cursor.fetchone()

        if matched_claim:
            now_str = _now_iso()
            return {
                "flag_type": "REUSED_EVIDENCE_HASH",
                "type": "REUSED_EVIDENCE_HASH",
                "similarity_score": 96,
                "similarity": 96,
                "confidence": 96,
                "status": "REVIEW_REQUIRED",
                "review_status": "REVIEW_REQUIRED",
                "reason": (
                    f"Evidence image appears similar to evidence submitted in another claim "
                    f"(Claim '{matched_claim['claim_id']}'). "
                    f"Field inspection recommended."
                ),
                "related_record": matched_claim["claim_id"],
                "created_at": now_str,
                "created_timestamp": now_str,
            }

    return None
