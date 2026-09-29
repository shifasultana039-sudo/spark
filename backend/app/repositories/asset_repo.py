"""
Foundational and business repository for Digital Asset Verification and Disaster Claims.
Provides complete CRUD, readable unique ID generation (AST-YYYY-NNNNNN),
and cryptographic baseline hash computation for citizen assets.
"""

import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from ..core.database import get_db


def compute_asset_integrity_hash(
    asset_id: str,
    household_ref: str,
    category: str,
    documented_value: float,
    purchase_date: str,
    location_address: str
) -> str:
    """Computes deterministic cryptographic baseline hash for an asset."""
    raw = f"{asset_id}|{household_ref}|{category}|{documented_value}|{purchase_date or ''}|{location_address}"
    return "0x" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_asset_dict(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalizes database row to ensure all expected output fields are populated."""
    if not row:
        return None
    d = dict(row)
    # Ensure aliases
    d["approximate_value"] = d.get("documented_value", 0.0)
    d["location"] = d.get("location_address", "")
    d["household"] = d.get("household_ref", "")
    d["registration_timestamp"] = d.get("created_at", "")
    return d


def normalize_claim_dict(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalizes database row to ensure all expected claim output fields and aliases are populated."""
    if not row:
        return None
    d = dict(row)
    d["household"] = d.get("household_ref", "")
    d["disaster_event"] = d.get("disaster_id", "")
    d["pre_disaster_verification_state"] = d.get("pre_disaster_verification_status", "UNVERIFIED")
    d["claim_status"] = d.get("review_status", "SUBMITTED")
    d["status"] = d.get("review_status", "SUBMITTED")
    d["created_timestamp"] = d.get("created_at", "")
    loc = d.get("location") or d.get("location_address") or "Katpadi, Vellore, Tamil Nadu"
    d["location"] = loc
    d["location_address"] = loc
    if d.get("evidence_confidence") is None:
        d["evidence_confidence"] = 85 if d.get("pre_disaster_verification_status") == "VERIFIED" else 65
    if not d.get("damage_category"):
        d["damage_category"] = "PENDING_ASSESSMENT"
    return d


class AssetRepository:
    """Encapsulates data access queries for citizen asset registry and disaster claims."""

    @staticmethod
    def generate_asset_id(year: Optional[int] = None) -> str:
        """
        Generates readable sequential unique IDs matching the pattern:
        AST-2026-000001
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        prefix = f"AST-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT asset_id FROM assets WHERE asset_id LIKE ? ORDER BY asset_id DESC;", (f"{prefix}%",))
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                aid = r.get("asset_id") or ""
                parts = aid.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def ensure_household_exists(household_ref: str, head_of_household: str, address: str = "") -> None:
        """Guarantees household existence to satisfy foreign key constraints."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM households WHERE household_ref = ?;", (household_ref,))
            if not cursor.fetchone():
                now_iso = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES (?, ?, ?, 'Vellore', 'Tamil Nadu', ?, ?);
                """, (household_ref, head_of_household, address or "Katpadi", now_iso, now_iso))

    @staticmethod
    def create_asset(
        category: str,
        description: str,
        documented_value: float,
        location_address: str,
        household_ref: str,
        purchase_date: Optional[str] = None,
        citizen_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """Creates a new citizen asset in UNVERIFIED state with unique readable ID."""
        now_iso = datetime.now(timezone.utc).isoformat()
        asset_id = AssetRepository.generate_asset_id()

        # Compute tamper-evident integrity hash
        integrity_hash = compute_asset_integrity_hash(
            asset_id=asset_id,
            household_ref=household_ref,
            category=category,
            documented_value=documented_value,
            purchase_date=purchase_date or "",
            location_address=location_address
        )

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO assets (
                asset_id, citizen_id, household_ref, category, description,
                documented_value, purchase_date, location_address, latitude,
                longitude, status, verification_confidence, integrity_hash,
                current_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNVERIFIED', 0, ?, 'INTACT', ?, ?);
            """, (
                asset_id, citizen_id, household_ref, category, description,
                documented_value, purchase_date, location_address, latitude,
                longitude, integrity_hash, now_iso, now_iso
            ))

        return AssetRepository.get_asset_by_id(asset_id)

    @staticmethod
    def get_asset_by_id(asset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single asset record by its unique asset_id."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            row = cursor.fetchone()
            return normalize_asset_dict(row)

    @staticmethod
    def list_assets(
        citizen_id: Optional[int] = None,
        household_ref: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Lists assets with flexible scoping for citizen isolation or admin queries."""
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM assets WHERE 1=1"
            params: List[Any] = []

            if citizen_id is not None:
                query += " AND citizen_id = ?"
                params.append(citizen_id)

            if household_ref is not None:
                query += " AND household_ref = ?"
                params.append(household_ref)

            if category is not None:
                query += " AND (category = ? OR category LIKE ?)"
                params.extend([category, f"%{category}%"])

            if status is not None:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY id DESC LIMIT ?;"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [normalize_asset_dict(r) for r in rows]

    @staticmethod
    def update_asset(asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates asset fields and recalculates integrity hash."""
        existing = AssetRepository.get_asset_by_id(asset_id)
        if not existing:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()

        # Merge fields
        category = updates.get("category") or existing["category"]
        description = updates.get("description") or existing["description"]
        documented_value = (
            updates.get("documented_value")
            if updates.get("documented_value") is not None
            else existing["documented_value"]
        )
        location_address = (
            updates.get("location_address")
            or updates.get("location")
            or existing["location_address"]
        )
        purchase_date = (
            updates.get("purchase_date")
            if updates.get("purchase_date") is not None
            else existing.get("purchase_date")
        )
        household_ref = (
            updates.get("household_ref")
            or updates.get("household")
            or existing["household_ref"]
        )
        current_status = updates.get("current_status") or existing.get("current_status", "INTACT")
        latitude = updates.get("latitude") if updates.get("latitude") is not None else existing.get("latitude")
        longitude = updates.get("longitude") if updates.get("longitude") is not None else existing.get("longitude")

        # Do NOT allow marking as VERIFIED in Asset Registry
        new_status = updates.get("status") or existing.get("status", "UNVERIFIED")
        if new_status.upper() == "VERIFIED":
            new_status = existing.get("status", "UNVERIFIED")

        # Recompute hash
        new_hash = compute_asset_integrity_hash(
            asset_id=asset_id,
            household_ref=household_ref,
            category=category,
            documented_value=documented_value,
            purchase_date=purchase_date or "",
            location_address=location_address
        )

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE assets
            SET category = ?, description = ?, documented_value = ?, location_address = ?,
                purchase_date = ?, household_ref = ?, current_status = ?, latitude = ?,
                longitude = ?, status = ?, integrity_hash = ?, updated_at = ?
            WHERE asset_id = ?;
            """, (
                category, description, documented_value, location_address,
                purchase_date, household_ref, current_status, latitude,
                longitude, new_status, new_hash, now_iso, asset_id
            ))

        return AssetRepository.get_asset_by_id(asset_id)

    @staticmethod
    def generate_evidence_id(year: Optional[int] = None) -> str:
        """Generates readable unique evidence ID matching EV-YYYY-NNNNNN."""
        if year is None:
            year = datetime.now(timezone.utc).year
        prefix = f"EV-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT evidence_id FROM asset_evidence WHERE evidence_id LIKE ? ORDER BY evidence_id DESC;", (f"{prefix}%",))
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                eid = r.get("evidence_id") or ""
                parts = eid.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def add_evidence(
        asset_id: str,
        evidence_type: str,
        file_url: str,
        original_filename: str,
        sha256_hash: str,
        file_size: int,
        mime_type: str,
        uploader: str,
        captured_timestamp: Optional[str] = None,
        metadata_json: Optional[str] = "{}",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        verification_status: str = "PENDING",
        score_contribution: int = 0
    ) -> Dict[str, Any]:
        """Inserts evidence item with PENDING verification status."""
        evidence_id = AssetRepository.generate_evidence_id()
        now_iso = datetime.now(timezone.utc).isoformat()
        captured_time = captured_timestamp or now_iso

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO asset_evidence (
                evidence_id, asset_id, evidence_type, file_url, original_filename,
                sha256_hash, file_size, mime_type, uploader, verification_status,
                score_contribution, captured_timestamp, metadata_json,
                latitude, longitude, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                evidence_id, asset_id, evidence_type, file_url, original_filename,
                sha256_hash, file_size, mime_type, uploader, verification_status,
                score_contribution, captured_time, metadata_json or "{}",
                latitude, longitude, now_iso, now_iso
            ))

        return AssetRepository.get_evidence_by_id(evidence_id)

    @staticmethod
    def get_evidence_by_id(evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single evidence item with linked asset ownership metadata from either asset or claim evidence."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT e.*, a.citizen_id AS asset_citizen_id, a.household_ref AS asset_household_ref
            FROM asset_evidence e
            LEFT JOIN assets a ON e.asset_id = a.asset_id
            WHERE e.evidence_id = ?;
            """, (evidence_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            # Fallback to claim_evidence
            cursor.execute("""
            SELECT e.*, c.asset_id, a.citizen_id AS asset_citizen_id, c.household_ref AS asset_household_ref
            FROM claim_evidence e
            LEFT JOIN disaster_claims c ON e.claim_id = c.claim_id
            LEFT JOIN assets a ON c.asset_id = a.asset_id
            WHERE e.evidence_id = ?;
            """, (evidence_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_evidence_for_asset(asset_id: str) -> List[Dict[str, Any]]:
        """Retrieves all evidence associated with a specific asset."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM asset_evidence WHERE asset_id = ? ORDER BY id DESC;", (asset_id,))
            return cursor.fetchall()

    @staticmethod
    def generate_verification_id(year: Optional[int] = None) -> str:
        """Generates readable unique verification ID matching VRF-YYYY-NNNNNN."""
        if year is None:
            year = datetime.now(timezone.utc).year
        prefix = f"VRF-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT verification_id FROM asset_verifications WHERE verification_id LIKE ? ORDER BY verification_id DESC;", (f"{prefix}%",))
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                vid = r.get("verification_id") or ""
                parts = vid.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def save_verification(
        asset_id: str,
        confidence_score: int,
        verification_status: str,
        evaluated_by: str,
        scoring_details_json: str,
        contributions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Records a new verification history entry and updates the asset's active verification state."""
        verification_id = AssetRepository.generate_verification_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO asset_verifications (
                verification_id, asset_id, confidence_score, verification_status,
                evaluated_by, scoring_details_json, verified_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                verification_id, asset_id, confidence_score, verification_status,
                evaluated_by, scoring_details_json, now_iso, now_iso
            ))

            cursor.execute("""
            UPDATE assets
            SET status = ?, verification_confidence = ?, updated_at = ?
            WHERE asset_id = ?;
            """, (verification_status, confidence_score, now_iso, asset_id))

            if contributions:
                for c in contributions:
                    ev_id = c.get("evidence_id")
                    weight = c.get("weight", 0)
                    if ev_id:
                        cursor.execute("""
                        UPDATE asset_evidence
                        SET verification_status = 'VERIFIED', score_contribution = ?, updated_at = ?
                        WHERE evidence_id = ?;
                        """, (weight, now_iso, ev_id))

        return {
            "verification_id": verification_id,
            "asset_id": asset_id,
            "confidence_score": confidence_score,
            "verification_status": verification_status,
            "evaluated_by": evaluated_by,
            "scoring_details_json": scoring_details_json,
            "verified_at": now_iso,
            "created_at": now_iso
        }

    @staticmethod
    def get_latest_verification(asset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent verification evaluation for an asset."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM asset_verifications
            WHERE asset_id = ?
            ORDER BY id DESC LIMIT 1;
            """, (asset_id,))
            return cursor.fetchone()

    @staticmethod
    def get_verification_history(asset_id: str) -> List[Dict[str, Any]]:
        """Retrieves complete chronological verification history for an asset."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM asset_verifications
            WHERE asset_id = ?
            ORDER BY id DESC;
            """, (asset_id,))
            return cursor.fetchall()

    @staticmethod
    def generate_certificate_id(year: Optional[int] = None) -> str:
        """
        Generates readable sequential unique IDs matching the pattern:
        CERT-2026-000001
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        prefix = f"CERT-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT certificate_id FROM asset_certificates WHERE certificate_id LIKE ? ORDER BY id DESC;", (f"{prefix}%",))
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                cid = r.get("certificate_id") or ""
                parts = cid.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def save_certificate(
        certificate_id: str,
        asset_id: str,
        certificate_token: str,
        verification_status: str,
        evidence_confidence: int,
        evidence_hash: str,
        qr_payload: str,
        issued_at: Optional[str] = None,
        verify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inserts or updates an asset digital certificate record,
        and links the certificate token and QR code URL to the asset.
        """
        now_iso = issued_at or datetime.now(timezone.utc).isoformat()
        verification_endpoint = verify_url or f"/certificates/verify/{certificate_token}"

        with get_db() as conn:
            cursor = conn.cursor()
            # Check if certificate exists for asset
            cursor.execute("SELECT id FROM asset_certificates WHERE asset_id = ? OR certificate_id = ?;", (asset_id, certificate_id))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                UPDATE asset_certificates
                SET certificate_id = ?, certificate_token = ?, verification_status = ?,
                    evidence_confidence = ?, evidence_hash = ?, issued_at = ?, qr_payload = ?
                WHERE id = ?;
                """, (
                    certificate_id, certificate_token, verification_status,
                    evidence_confidence, evidence_hash, now_iso, qr_payload,
                    existing["id"]
                ))
            else:
                cursor.execute("""
                INSERT INTO asset_certificates (
                    certificate_id, asset_id, certificate_token, verification_status,
                    evidence_confidence, evidence_hash, issued_at, qr_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    certificate_id, asset_id, certificate_token, verification_status,
                    evidence_confidence, evidence_hash, now_iso, qr_payload
                ))

            # Update asset record with certificate token and verification URL
            cursor.execute("""
            UPDATE assets
            SET certificate_token = ?, qr_code_url = ?, updated_at = ?
            WHERE asset_id = ?;
            """, (certificate_token, verification_endpoint, now_iso, asset_id))

        return AssetRepository.get_certificate_by_id(certificate_id)

    @staticmethod
    def get_certificate_by_id(certificate_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves single certificate by certificate_id or certificate_token,
        joining the asset to include category, description, and registration timestamp.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*,
                   a.category,
                   a.description,
                   a.created_at AS registration_timestamp,
                   a.citizen_id,
                   a.household_ref,
                   a.location_address,
                   a.documented_value,
                   a.current_status
            FROM asset_certificates c
            JOIN assets a ON c.asset_id = a.asset_id
            WHERE c.certificate_id = ? OR c.certificate_token = ?;
            """, (certificate_id, certificate_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_certificate_by_asset_id(asset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves certificate associated with a specific asset."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*,
                   a.category,
                   a.description,
                   a.created_at AS registration_timestamp,
                   a.citizen_id,
                   a.household_ref,
                   a.location_address,
                   a.documented_value,
                   a.current_status
            FROM asset_certificates c
            JOIN assets a ON c.asset_id = a.asset_id
            WHERE c.asset_id = ?;
            """, (asset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_certificate_by_token(token: str) -> Optional[Dict[str, Any]]:
        """Retrieves certificate by secure verification token."""
        return AssetRepository.get_certificate_by_id(token)

    @staticmethod
    def generate_claim_id(year: Optional[int] = None) -> str:
        """
        Generates readable sequential unique IDs matching the pattern:
        CLM-2026-010291
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        prefix = f"CLM-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT claim_id FROM disaster_claims WHERE claim_id LIKE ? ORDER BY id DESC;", (f"{prefix}%",))
            rows = cursor.fetchall()
            max_num = 10290  # Base threshold so the first generated starts at 010291
            for r in rows:
                cid = r.get("claim_id") or ""
                parts = cid.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def create_claim(
        asset_id: str,
        household_ref: str,
        disaster_id: str,
        damage_description: str,
        pre_disaster_verification_status: str,
        review_status: str = "SUBMITTED",
        claim_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new disaster claim record in SUBMITTED state."""
        cid = claim_id or AssetRepository.generate_claim_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO disaster_claims (
                claim_id, asset_id, household_ref, disaster_id, damage_description,
                pre_disaster_verification_status, review_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cid, asset_id, household_ref, disaster_id, damage_description,
                pre_disaster_verification_status, review_status, now_iso, now_iso
            ))

        return AssetRepository.get_claim_by_id(cid)

    @staticmethod
    def get_claim_by_id(claim_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single disaster claim by its unique claim_id."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*,
                   a.citizen_id,
                   a.category AS asset_category,
                   a.description AS asset_description,
                   a.location_address AS location,
                   a.location_address,
                   COALESCE(da.overall_confidence, a.verification_confidence, 85) AS evidence_confidence,
                   COALESCE(da.damage_category, 'PENDING_ASSESSMENT') AS damage_category,
                   COALESCE(da.estimated_damage_percentage, va.estimated_damage_percentage) AS estimated_damage_percentage,
                   COALESCE(da.estimated_damage_percentage, va.estimated_damage_percentage) AS damage_percentage,
                   va.approved_compensation_amount,
                   va.indicative_loss_amount
            FROM disaster_claims c
            LEFT JOIN assets a ON c.asset_id = a.asset_id
            LEFT JOIN damage_assessments da ON c.claim_id = da.claim_id
            LEFT JOIN value_assessments va ON c.claim_id = va.claim_id
            WHERE c.claim_id = ?;
            """, (claim_id,))
            row = cursor.fetchone()
            return normalize_claim_dict(row)

    @staticmethod
    def list_claims(
        citizen_id: Optional[int] = None,
        household_ref: Optional[str] = None,
        status_filter: Optional[str] = None,
        disaster_id: Optional[str] = None,
        asset_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Lists disaster claims with scoping for citizen isolation or officer queries."""
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
            SELECT c.*,
                   a.citizen_id,
                   a.category AS asset_category,
                   a.description AS asset_description,
                   a.location_address AS location,
                   a.location_address,
                   COALESCE(da.overall_confidence, a.verification_confidence, 85) AS evidence_confidence,
                   COALESCE(da.damage_category, 'PENDING_ASSESSMENT') AS damage_category,
                   COALESCE(da.estimated_damage_percentage, va.estimated_damage_percentage) AS estimated_damage_percentage,
                   COALESCE(da.estimated_damage_percentage, va.estimated_damage_percentage) AS damage_percentage,
                   va.approved_compensation_amount,
                   va.indicative_loss_amount
            FROM disaster_claims c
            LEFT JOIN assets a ON c.asset_id = a.asset_id
            LEFT JOIN damage_assessments da ON c.claim_id = da.claim_id
            LEFT JOIN value_assessments va ON c.claim_id = va.claim_id
            WHERE 1=1
            """
            params: List[Any] = []

            if citizen_id is not None and household_ref is not None:
                query += " AND (a.citizen_id = ? OR c.household_ref = ?)"
                params.extend([citizen_id, household_ref])
            elif citizen_id is not None:
                query += " AND a.citizen_id = ?"
                params.append(citizen_id)
            elif household_ref is not None:
                query += " AND c.household_ref = ?"
                params.append(household_ref)

            if status_filter is not None:
                query += " AND (c.review_status = ? OR c.review_status LIKE ?)"
                params.extend([status_filter, f"%{status_filter}%"])

            if disaster_id is not None:
                query += " AND c.disaster_id = ?"
                params.append(disaster_id)

            if asset_id is not None:
                query += " AND c.asset_id = ?"
                params.append(asset_id)

            query += " ORDER BY c.id DESC LIMIT ?;"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [normalize_claim_dict(r) for r in rows]

    @staticmethod
    def generate_claim_evidence_id(year: Optional[int] = None) -> str:
        """Generates readable unique claim evidence ID matching CLM-EV-YYYY-NNNNNN."""
        if year is None:
            year = datetime.now(timezone.utc).year
        prefix = f"CLM-EV-{year}-"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT evidence_id FROM claim_evidence ORDER BY id DESC;")
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                eid = r.get("evidence_id") or ""
                parts = eid.split("-")
                if len(parts) >= 2 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            next_num = max_num + 1
            return f"{prefix}{next_num:06d}"

    @staticmethod
    def add_claim_evidence(
        claim_id: str,
        evidence_type: str,
        file_url: Optional[str],
        original_filename: str,
        sha256_hash: str,
        file_size: int,
        mime_type: str,
        captured_timestamp: Optional[str] = None,
        evidence_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inserts a post-disaster claim evidence item linked to a disaster claim."""
        if not evidence_id:
            evidence_id = AssetRepository.generate_claim_evidence_id()
        now_iso = datetime.now(timezone.utc).isoformat()
        captured_time = captured_timestamp or now_iso
        if not file_url:
            file_url = f"/claims/{claim_id}/evidence/{evidence_id}/file"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO claim_evidence (
                evidence_id, claim_id, evidence_type, file_url, original_filename,
                sha256_hash, file_size, mime_type, captured_timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                evidence_id, claim_id, evidence_type, file_url, original_filename,
                sha256_hash, file_size, mime_type, captured_time, now_iso
            ))

        return AssetRepository.get_claim_evidence_by_id(evidence_id)

    @staticmethod
    def get_claim_evidence_by_id(evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single claim evidence item with joined claim and asset ownership metadata."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT e.*,
                   c.asset_id,
                   c.household_ref AS claim_household_ref,
                   c.household_ref AS asset_household_ref,
                   a.citizen_id AS asset_citizen_id
            FROM claim_evidence e
            LEFT JOIN disaster_claims c ON e.claim_id = c.claim_id
            LEFT JOIN assets a ON c.asset_id = a.asset_id
            WHERE e.evidence_id = ?;
            """, (evidence_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["uploader"] = "Citizen"
            d["metadata_json"] = "{}"
            d["verification_status"] = "PENDING"
            d["score_contribution"] = 0
            return d

    @staticmethod
    def list_evidence_for_claim(claim_id: str) -> List[Dict[str, Any]]:
        """Retrieves all post-disaster evidence associated with a specific disaster claim."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT e.*, c.asset_id
            FROM claim_evidence e
            LEFT JOIN disaster_claims c ON e.claim_id = c.claim_id
            WHERE e.claim_id = ?
            ORDER BY e.id DESC;
            """, (claim_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["uploader"] = "Citizen"
                result.append(d)
            return result

    @staticmethod
    def save_damage_assessment(
        claim_id: str,
        damage_detected: bool,
        damage_category: str,
        estimated_damage_percentage: int,
        asset_match_confidence: int,
        evidence_quality: int,
        overall_confidence: int,
        explanation: str,
        provider_name: str,
        assessment_mode: str = "DEMO_SIMULATION"
    ) -> Dict[str, Any]:
        """Saves a damage assessment for a claim."""
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # We need to make sure damage_assessments table exists, but we'll assume it exists or use dict if we just want to mock it.
        # Let's insert into database. If it fails due to missing table, we'll need to create it.
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create table if not exists (to be safe)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS damage_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL,
                damage_detected BOOLEAN,
                damage_category TEXT,
                estimated_damage_percentage INTEGER,
                asset_match_confidence INTEGER,
                evidence_quality INTEGER,
                overall_confidence INTEGER,
                explanation TEXT,
                provider_name TEXT,
                assessment_mode TEXT DEFAULT 'DEMO_SIMULATION',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id)
            );
            """)

            cursor.execute("PRAGMA table_info(damage_assessments);")
            cols = [row["name"] for row in cursor.fetchall()]
            if "assessment_mode" not in cols:
                cursor.execute("ALTER TABLE damage_assessments ADD COLUMN assessment_mode TEXT DEFAULT 'DEMO_SIMULATION';")
            if "updated_at" not in cols:
                cursor.execute("ALTER TABLE damage_assessments ADD COLUMN updated_at TEXT;")

            cursor.execute("""
            INSERT OR REPLACE INTO damage_assessments (
                claim_id, damage_detected, damage_category, estimated_damage_percentage,
                asset_match_confidence, evidence_quality, overall_confidence,
                explanation, provider_name, assessment_mode, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                claim_id, damage_detected, damage_category, estimated_damage_percentage,
                asset_match_confidence, evidence_quality, overall_confidence,
                explanation, provider_name, assessment_mode, now_iso, now_iso
            ))
            
            cursor.execute("""
            UPDATE disaster_claims 
            SET review_status = 'AI_ASSESSED', updated_at = ? 
            WHERE claim_id = ?;
            """, (now_iso, claim_id))
            
            # Fetch the inserted record
            cursor.execute("SELECT * FROM damage_assessments WHERE claim_id = ? ORDER BY id DESC LIMIT 1;", (claim_id,))
            row = dict(cursor.fetchone())
            
            return row

    @staticmethod
    def get_damage_assessment_for_claim(claim_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest damage assessment for a claim, if available."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS damage_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL,
                damage_detected BOOLEAN,
                damage_category TEXT,
                estimated_damage_percentage INTEGER,
                asset_match_confidence INTEGER,
                evidence_quality INTEGER,
                overall_confidence INTEGER,
                explanation TEXT,
                provider_name TEXT,
                assessment_mode TEXT DEFAULT 'DEMO_SIMULATION',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id)
            );
            """)
            cursor.execute(
                "SELECT * FROM damage_assessments WHERE claim_id = ? ORDER BY id DESC LIMIT 1;",
                (claim_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @staticmethod
    def save_value_assessment(
        claim_id: str,
        original_documented_value: float,
        reference_current_value: float,
        depreciation_percent: float,
        estimated_damage_percentage: int,
        indicative_loss_amount: float,
        is_ai_assisted: int = 1
    ) -> Dict[str, Any]:
        """Persists indicative value/loss assessment for a claim."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS value_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT UNIQUE NOT NULL,
                original_documented_value REAL NOT NULL,
                depreciation_percent REAL NOT NULL DEFAULT 0.0,
                reference_current_value REAL NOT NULL,
                estimated_damage_percentage INTEGER NOT NULL,
                indicative_loss_amount REAL NOT NULL,
                approved_compensation_amount REAL,
                officer_notes TEXT,
                is_ai_assisted INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
            );
            """)
            cursor.execute("""
            INSERT OR REPLACE INTO value_assessments (
                claim_id, original_documented_value, depreciation_percent, reference_current_value,
                estimated_damage_percentage, indicative_loss_amount, is_ai_assisted, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                claim_id, original_documented_value, depreciation_percent, reference_current_value,
                estimated_damage_percentage, indicative_loss_amount, is_ai_assisted, now_iso
            ))
            cursor.execute("SELECT * FROM value_assessments WHERE claim_id = ? ORDER BY id DESC LIMIT 1;", (claim_id,))
            return dict(cursor.fetchone())

    @staticmethod
    def get_value_assessment_for_claim(claim_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves existing value/loss assessment for a claim."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS value_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT UNIQUE NOT NULL,
                original_documented_value REAL NOT NULL,
                depreciation_percent REAL NOT NULL DEFAULT 0.0,
                reference_current_value REAL NOT NULL,
                estimated_damage_percentage INTEGER NOT NULL,
                indicative_loss_amount REAL NOT NULL,
                approved_compensation_amount REAL,
                officer_notes TEXT,
                is_ai_assisted INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
            );
            """)
            cursor.execute("SELECT * FROM value_assessments WHERE claim_id = ? ORDER BY id DESC LIMIT 1;", (claim_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @staticmethod
    def update_claim_decision(
        claim_id: str,
        review_status: str,
        officer_decision: str
    ) -> Optional[Dict[str, Any]]:
        """Updates claim review status and officer decision."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE disaster_claims
            SET review_status = ?, officer_decision = ?, updated_at = ?
            WHERE claim_id = ?;
            """, (review_status, officer_decision, now_iso, claim_id))
        return AssetRepository.get_claim_by_id(claim_id)

    @staticmethod
    def approve_claim_compensation(
        claim_id: str,
        approved_amount: float,
        notes: Optional[str] = None
    ) -> None:
        """Records approved compensation amount in value_assessments table."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE value_assessments
            SET approved_compensation_amount = ?, officer_notes = ?
            WHERE claim_id = ?;
            """, (approved_amount, notes, claim_id))

    @staticmethod
    def modify_claim_damage_assessment(
        claim_id: str,
        damage_percentage: int,
        damage_category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """Modifies existing damage assessment or creates updated record and recalculates loss."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            if damage_category:
                cursor.execute("""
                UPDATE damage_assessments
                SET estimated_damage_percentage = ?, damage_category = ?, explanation = ?, updated_at = ?
                WHERE claim_id = ?;
                """, (damage_percentage, damage_category, f"Officer adjusted: {notes or ''}", now_iso, claim_id))
            else:
                cursor.execute("""
                UPDATE damage_assessments
                SET estimated_damage_percentage = ?, explanation = ?, updated_at = ?
                WHERE claim_id = ?;
                """, (damage_percentage, f"Officer adjusted: {notes or ''}", now_iso, claim_id))

            # Recalculate loss in value_assessments if present
            cursor.execute("SELECT reference_current_value FROM value_assessments WHERE claim_id = ?;", (claim_id,))
            va_row = cursor.fetchone()
            if va_row:
                ref_val = float(va_row["reference_current_value"])
                new_loss = round(ref_val * (damage_percentage / 100.0), 2)
                cursor.execute("""
                UPDATE value_assessments
                SET estimated_damage_percentage = ?, indicative_loss_amount = ?
                WHERE claim_id = ?;
                """, (damage_percentage, new_loss, claim_id))

    # -------------------------------------------------------------
    # Step 28: Field Inspection & Assessor Methods
    # -------------------------------------------------------------
    @staticmethod
    def get_field_inspections(
        status: Optional[str] = None,
        assigned_officer: Optional[str] = None,
        claim_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves field inspections with enriched claim and asset details."""
        query = """
        SELECT
            fi.id,
            fi.inspection_id,
            fi.claim_id,
            fi.assigned_officer,
            fi.status,
            fi.findings,
            fi.damage_rating,
            fi.report_file_url,
            fi.created_at,
            fi.completed_at,
            dc.asset_id,
            dc.household_ref,
            dc.damage_description,
            dc.review_status AS claim_status,
            ast.category AS asset_category,
            ast.description AS asset_description,
            ast.documented_value,
            ast.location_address,
            (SELECT COUNT(*) FROM claim_evidence ce WHERE ce.claim_id = fi.claim_id) as evidence_count
        FROM field_inspections fi
        LEFT JOIN disaster_claims dc ON fi.claim_id = dc.claim_id
        LEFT JOIN assets ast ON dc.asset_id = ast.asset_id
        WHERE 1=1
        """
        params: List[Any] = []
        if status and status.upper() != "ALL":
            query += " AND UPPER(fi.status) = ?"
            params.append(status.strip().upper())
        if claim_id:
            query += " AND fi.claim_id = ?"
            params.append(claim_id.strip())
        if assigned_officer:
            query += " AND (fi.assigned_officer LIKE ? OR ? LIKE '%' || fi.assigned_officer || '%')"
            params.append(f"%{assigned_officer.strip()}%")
            params.append(assigned_officer.strip())

        query += " ORDER BY fi.id DESC;"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_field_inspection_by_id(inspection_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single field inspection with complete dossier including evidence."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT
                fi.id,
                fi.inspection_id,
                fi.claim_id,
                fi.assigned_officer,
                fi.status,
                fi.findings,
                fi.damage_rating,
                fi.report_file_url,
                fi.created_at,
                fi.completed_at,
                dc.asset_id,
                dc.household_ref,
                dc.damage_description,
                dc.review_status AS claim_status,
                ast.category AS asset_category,
                ast.description AS asset_description,
                ast.documented_value,
                ast.location_address,
                (SELECT COUNT(*) FROM claim_evidence ce WHERE ce.claim_id = fi.claim_id) as evidence_count
            FROM field_inspections fi
            LEFT JOIN disaster_claims dc ON fi.claim_id = dc.claim_id
            LEFT JOIN assets ast ON dc.asset_id = ast.asset_id
            WHERE fi.inspection_id = ? OR fi.id = ?;
            """, (inspection_id, inspection_id))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)

            # Retrieve evidence files for this claim
            cursor.execute("""
            SELECT id, evidence_id, claim_id, evidence_type, file_url, original_filename,
                   sha256_hash, file_size, mime_type, captured_timestamp, created_at
            FROM claim_evidence
            WHERE claim_id = ?
            ORDER BY id DESC;
            """, (res["claim_id"],))
            res["evidence_files"] = [dict(ev) for ev in cursor.fetchall()]
            return res

    @staticmethod
    def get_field_inspection_by_claim_id(claim_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves field inspection for a given claim ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT inspection_id FROM field_inspections WHERE claim_id = ? ORDER BY id DESC LIMIT 1;
            """, (claim_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return AssetRepository.get_field_inspection_by_id(row["inspection_id"])

    @staticmethod
    def create_or_update_field_inspection(
        claim_id: str,
        assigned_officer: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = "PENDING"
    ) -> Dict[str, Any]:
        """Creates or updates a field inspection task for a forwarded claim."""
        now_iso = datetime.now(timezone.utc).isoformat()
        officer = assigned_officer or "Katpadi Youth Emergency Corps (NGO)"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT inspection_id, findings FROM field_inspections WHERE claim_id = ? ORDER BY id DESC LIMIT 1;", (claim_id,))
            existing = cursor.fetchone()
            if existing:
                insp_id = existing["inspection_id"]
                combined_findings = notes or existing["findings"]
                cursor.execute("""
                UPDATE field_inspections
                SET assigned_officer = ?, status = ?, findings = ?
                WHERE inspection_id = ?;
                """, (officer, status, combined_findings, insp_id))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM field_inspections;")
                cnt = cursor.fetchone()["count"] + 1
                insp_id = f"INSP-2026-{cnt:04d}"
                cursor.execute("""
                INSERT INTO field_inspections (inspection_id, claim_id, assigned_officer, status, findings, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (insp_id, claim_id, officer, status, notes, now_iso))

        return AssetRepository.get_field_inspection_by_id(insp_id)

    @staticmethod
    def update_field_inspection_findings(
        inspection_id: str,
        findings: str,
        damage_rating: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates inspection findings and damage rating."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM field_inspections WHERE inspection_id = ?;", (inspection_id,))
            existing = cursor.fetchone()
            if not existing:
                return None

            new_status = status or ("IN_PROGRESS" if existing["status"] == "PENDING" else existing["status"])
            if damage_rating:
                cursor.execute("""
                UPDATE field_inspections
                SET findings = ?, damage_rating = ?, status = ?
                WHERE inspection_id = ?;
                """, (findings, damage_rating, new_status, inspection_id))
            else:
                cursor.execute("""
                UPDATE field_inspections
                SET findings = ?, status = ?
                WHERE inspection_id = ?;
                """, (findings, new_status, inspection_id))

        return AssetRepository.get_field_inspection_by_id(inspection_id)

    @staticmethod
    def submit_field_inspection_report(
        inspection_id: str,
        findings: str,
        damage_rating: str,
        report_file_url: Optional[str] = None,
        completed_by: str = "Field Assessor"
    ) -> Optional[Dict[str, Any]]:
        """Finalizes inspection report, marks status COMPLETED, and updates claim."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT claim_id FROM field_inspections WHERE inspection_id = ?;", (inspection_id,))
            insp = cursor.fetchone()
            if not insp:
                return None

            claim_id = insp["claim_id"]
            cursor.execute("""
            UPDATE field_inspections
            SET status = 'COMPLETED', findings = ?, damage_rating = ?, report_file_url = COALESCE(?, report_file_url), completed_at = ?
            WHERE inspection_id = ?;
            """, (findings, damage_rating, report_file_url, now_iso, inspection_id))

            # Update claim review_status and decision note so government officer sees it
            decision_summary = f"FIELD_INSPECTION_COMPLETED: Damage assessed as {damage_rating} by {completed_by}. Findings: {findings[:120]}"
            cursor.execute("""
            UPDATE disaster_claims
            SET review_status = 'FIELD_INSPECTED', officer_decision = ?, updated_at = ?
            WHERE claim_id = ?;
            """, (decision_summary, now_iso, claim_id))

        return AssetRepository.get_field_inspection_by_id(inspection_id)




