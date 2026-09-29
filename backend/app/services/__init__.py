"""
Service layer exposing domain calculation engines, verification logic, and blockchain services.
"""

try:
    from services.trust_engine import calculate_trust_score
    from services.priority_engine import calculate_priority_score
    from services.allocation_engine import calculate_resource_allocation
    from services.explanation_engine import generate_decision_explanation
    from services.fraud_engine import analyze_report_cluster
    from services.blockchain_service import MSTBlockchainService, compute_decision_hash
    from services.integrity_service import (
        record_audit_event,
        verify_audit_chain,
        verify_single_record,
        get_audit_records,
        format_audit_record,
        log_asset_registered,
        log_evidence_added,
        log_verification_updated,
        log_certificate_generated,
        log_claim_created,
        log_ai_assessment_created,
        log_officer_reviewed
    )
    from services.asset_verification_engine import evaluate_asset_evidence, generate_certificate_payload
    from services.damage_assessment_engine import DemoDamageAssessmentProvider, cv_provider
    from services.value_assessment_engine import compute_indicative_loss
    from services.loss_assessment_engine import loss_engine
    from services.anomaly_detection_service import (
        check_evidence_anomalies,
        run_anomaly_detection,
        get_persisted_anomalies,
    )
except (ImportError, ValueError):
    from ..services.trust_engine import calculate_trust_score
    from ..services.priority_engine import calculate_priority_score
    from ..services.allocation_engine import calculate_resource_allocation
    from ..services.explanation_engine import generate_decision_explanation
    from ..services.fraud_engine import analyze_report_cluster
    from ..services.blockchain_service import MSTBlockchainService, compute_decision_hash
    from ..services.integrity_service import (
        record_audit_event,
        verify_audit_chain,
        verify_single_record,
        get_audit_records,
        format_audit_record,
        log_asset_registered,
        log_evidence_added,
        log_verification_updated,
        log_certificate_generated,
        log_claim_created,
        log_ai_assessment_created,
        log_officer_reviewed
    )
    from ..services.asset_verification_engine import evaluate_asset_evidence, generate_certificate_payload
    from ..services.damage_assessment_engine import DemoDamageAssessmentProvider, cv_provider
    from ..services.value_assessment_engine import compute_indicative_loss
    from ..services.loss_assessment_engine import loss_engine
    from ..services.anomaly_detection_service import (
        check_evidence_anomalies,
        run_anomaly_detection,
        get_persisted_anomalies,
    )
