"""
Disaster management domain endpoints: reports, locations, resources, and recommendations.
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query

from ....repositories.disaster_repo import DisasterRepository
from ....schemas.disaster import (
    ReportCreate,
    RecommendationOverride,
    RecommendationAction,
    ResourceDispatchPayload
)
from ....core.database import get_db
from ....core.config import MST_EXPLORER_URL
from ....core.errors import NotFoundError, ValidationError
from ....utils.helpers import get_current_utc_iso
from ....services import (
    calculate_trust_score,
    analyze_report_cluster,
    MSTBlockchainService,
    compute_decision_hash,
    record_audit_event
)

router = APIRouter(tags=["Disaster Operations"])
blockchain_service = MSTBlockchainService()

@router.get("/users", summary="List available demo users and roles")
def list_users():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id ASC;")
        return cursor.fetchall()

@router.get("/locations", summary="List operational zones")
def list_locations():
    return DisasterRepository.get_locations()

@router.get("/disasters", summary="List declared disaster events")
def list_disasters():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM disasters ORDER BY id ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.get("/resources", summary="List relief resources and warehouse inventory")
def list_resources():
    return DisasterRepository.get_resources()

@router.post("/resources/dispatch", summary="Dispatch relief supplies")
def dispatch_resources(payload: ResourceDispatchPayload):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE type = ?;", (payload.resource_type,))
        res = cursor.fetchone()
        if not res:
            raise NotFoundError(f"Resource type '{payload.resource_type}' not found.")

        if res["available_quantity"] < payload.quantity:
            raise ValidationError(
                f"Insufficient inventory. Available: {res['available_quantity']}, Requested: {payload.quantity}"
            )

        new_avail = res["available_quantity"] - payload.quantity
        new_disp = res["dispatched_quantity"] + payload.quantity

        cursor.execute("""
        UPDATE resources
        SET available_quantity = ?, dispatched_quantity = ?
        WHERE type = ?;
        """, (new_avail, new_disp, payload.resource_type))

        record_audit_event(
            actor=payload.actor_name,
            role=payload.actor_role,
            event_type="RESOURCE_DISPATCH",
            entity_type="RESOURCE",
            entity_id=payload.resource_type,
            description=f"Dispatched {payload.quantity} {res['unit']} of {res['item_name']} to {payload.location_name}."
        )

        return {
            "status": "DISPATCHED",
            "resource_type": payload.resource_type,
            "dispatched_quantity": payload.quantity,
            "remaining_available": new_avail,
            "total_dispatched": new_disp
        }

@router.get("/reports", summary="List incoming field reports")
def list_reports(
    location: Optional[str] = Query(None, description="Filter by location name"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=500)
):
    reports = DisasterRepository.get_reports(location, severity, limit)
    for rep in reports:
        if isinstance(rep.get("required_resources"), str):
            try:
                rep["required_resources"] = json.loads(rep["required_resources"])
            except Exception:
                rep["required_resources"] = [r.strip() for r in rep["required_resources"].split(",") if r.strip()]
    return reports

@router.post("/reports", status_code=status.HTTP_201_CREATED, summary="Ingest new disaster field report")
def create_report(report: ReportCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM disaster_reports WHERE location = ?;", (report.location,))
        existing_reports = cursor.fetchall()

        cluster_result = analyze_report_cluster(
            new_report_desc=report.description,
            location=report.location,
            existing_reports=existing_reports
        )

        trust_result = calculate_trust_score(
            source=report.source,
            evidence_available=report.evidence_available or "None",
            has_cross_confirmation=cluster_result["is_duplicate_cluster"],
            is_recent=True,
            is_contradictory=cluster_result["is_conflicting"]
        )

        report_id = f"R-{uuid.uuid4().hex[:6].upper()}"
        now_iso = get_current_utc_iso()
        req_res_str = json.dumps(report.required_resources)

        cursor.execute("""
        INSERT INTO disaster_reports (
            report_id, source, location, sub_zone, latitude, longitude,
            description, people_affected, severity, required_resources,
            evidence_available, timestamp, trust_score, source_reliability_score,
            cross_confirmation_score, evidence_score, recency_score, consistency_penalty,
            verification_status, duplicate_cluster_id, is_contradictory, safety_gate_note,
            created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            report_id, report.source, report.location, report.sub_zone, report.latitude, report.longitude,
            report.description, report.people_affected, report.severity.upper(), req_res_str,
            report.evidence_available or "None", now_iso, trust_result["trust_score"],
            trust_result["source_reliability_score"], trust_result["cross_confirmation_score"],
            trust_result["evidence_score"], trust_result["recency_score"], trust_result["consistency_penalty"],
            trust_result["verification_status"], cluster_result["duplicate_cluster_id"],
            1 if cluster_result["is_conflicting"] else 0,
            cluster_result.get("conflict_reason"), now_iso
        ))

        record_audit_event(
            actor="Report Ingestion Service",
            role="SYSTEM",
            event_type="REPORT_INGESTION",
            entity_type="DISASTER_REPORT",
            entity_id=report_id,
            description=f"New report ingested from {report.source} for {report.location}. Trust Score: {trust_result['trust_score']}."
        )

        return {
            "report_id": report_id,
            "trust_score": trust_result["trust_score"],
            "verification_status": trust_result["verification_status"],
            "duplicate_cluster_id": cluster_result["duplicate_cluster_id"],
            "is_contradictory": cluster_result["is_conflicting"],
            "created_at": now_iso
        }

@router.get("/recommendations", summary="List AI recommendations")
def list_recommendations(status_filter: Optional[str] = Query(None, alias="status")):
    return DisasterRepository.get_recommendations(status_filter)

@router.post("/recommendations/{rec_id}/approve", summary="Supervisor approves resource recommendation")
def approve_recommendation(rec_id: str, action: RecommendationAction):
    rec = DisasterRepository.get_recommendation_by_id(rec_id)
    if not rec:
        raise NotFoundError("Recommendation not found.")

    now_iso = get_current_utc_iso()
    approved_qty = rec["recommended_quantity"]
    approver_wallet = action.wallet_address or "0x8a92B215E1D369Ac082f9bC488FeE3236e787f31"

    bc_record = blockchain_service.record_decision(
        decision_id=rec_id,
        report_hash=rec.get("report_hash") or compute_decision_hash(rec_id, rec["priority_score"], rec["confidence_score"], rec["resource_type"], approved_qty, "APPROVED"),
        priority_score=rec["priority_score"],
        confidence_score=rec["confidence_score"],
        resource_type=rec["resource_type"],
        quantity=approved_qty,
        status="APPROVED",
        approver_wallet=approver_wallet
    )

    DisasterRepository.update_recommendation_approval(
        rec_id=rec_id,
        approved_quantity=approved_qty,
        approver_name=action.actor_name,
        approved_at=now_iso,
        blockchain_tx_hash=bc_record["tx_hash"],
        block_number=bc_record["block_number"],
        approver_wallet=approver_wallet
    )

    record_audit_event(
        actor=action.actor_name,
        role=action.actor_role,
        event_type="RECOMMENDATION_APPROVAL",
        entity_type="RECOMMENDATION",
        entity_id=rec_id,
        description=f"Approved allocation of {approved_qty} units of {rec['resource_type']} for {rec['location_name']}.",
        blockchain_tx_hash=bc_record["tx_hash"]
    )

    return {
        "status": "APPROVED",
        "recommendation_id": rec_id,
        "approved_quantity": approved_qty,
        "approved_by": action.actor_name,
        "blockchain_tx_hash": bc_record["tx_hash"],
        "block_number": bc_record["block_number"],
        "explorer_url": f"{MST_EXPLORER_URL}/tx/{bc_record['tx_hash']}"
    }

@router.post("/recommendations/{rec_id}/modify", summary="Supervisor modifies recommended allocation")
def modify_recommendation(rec_id: str, override: RecommendationOverride):
    rec = DisasterRepository.get_recommendation_by_id(rec_id)
    if not rec:
        raise NotFoundError("Recommendation not found.")

    now_iso = get_current_utc_iso()
    bc_record = blockchain_service.record_decision(
        decision_id=rec_id,
        report_hash=compute_decision_hash(rec_id, rec["priority_score"], rec["confidence_score"], rec["resource_type"], override.modified_quantity, "HUMAN_OVERRIDDEN"),
        priority_score=rec["priority_score"],
        confidence_score=rec["confidence_score"],
        resource_type=rec["resource_type"],
        quantity=override.modified_quantity,
        status="HUMAN_OVERRIDDEN",
        approver_wallet="0x8a92B215E1D369Ac082f9bC488FeE3236e787f31"
    )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE recommendations
        SET status = 'APPROVED',
            approved_quantity = ?,
            human_override = 1,
            override_reason = ?,
            approved_by_supervisor_1 = ?,
            approved_at = ?,
            blockchain_tx_hash = ?,
            block_number = ?
        WHERE recommendation_id = ?;
        """, (
            override.modified_quantity, override.override_reason, override.supervisor_name,
            now_iso, bc_record["tx_hash"], bc_record["block_number"], rec_id
        ))

    record_audit_event(
        actor=override.supervisor_name,
        role=override.supervisor_role,
        event_type="RECOMMENDATION_OVERRIDE",
        entity_type="RECOMMENDATION",
        entity_id=rec_id,
        description=f"Human override: adjusted quantity from {rec['recommended_quantity']} to {override.modified_quantity}. Reason: {override.override_reason}",
        blockchain_tx_hash=bc_record["tx_hash"]
    )

    return {
        "status": "APPROVED",
        "human_override": True,
        "modified_quantity": override.modified_quantity,
        "override_reason": override.override_reason,
        "blockchain_tx_hash": bc_record["tx_hash"],
        "explorer_url": f"{MST_EXPLORER_URL}/tx/{bc_record['tx_hash']}"
    }

@router.post("/recommendations/{rec_id}/reject", summary="Reject recommendation")
def reject_recommendation(rec_id: str, action: RecommendationAction):
    rec = DisasterRepository.get_recommendation_by_id(rec_id)
    if not rec:
        raise NotFoundError("Recommendation not found.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE recommendations SET status = 'REJECTED' WHERE recommendation_id = ?;", (rec_id,))

    record_audit_event(
        actor=action.actor_name,
        role=action.actor_role,
        event_type="RECOMMENDATION_REJECT",
        entity_type="RECOMMENDATION",
        entity_id=rec_id,
        description=f"Rejected allocation for {rec['location_name']}."
    )

    return {"status": "REJECTED", "recommendation_id": rec_id}
