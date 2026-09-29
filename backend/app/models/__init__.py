"""
Domain model definitions, relational entities, and status enumerations for ReliefChain AI.
"""

from .entities import (
    # Enumerations
    UserRole,
    AssetCategory,
    AssetVerificationStatus,
    AssetPhysicalStatus,
    EvidenceType,
    EvidenceVerificationStatus,
    ClaimReviewStatus,
    DamageCategory,
    InspectionStatus,
    ReviewAction,
    AnomalyFlagStatus,
    AnomalyFlagType,
    # 13 Relational Domain Models
    UserModel,
    HouseholdModel,
    AssetModel,
    EvidenceModel,
    AssetVerificationModel,
    CertificateModel,
    DisasterClaimModel,
    DamageAssessmentModel,
    ValueAssessmentModel,
    AnomalyFlagModel,
    AuditEventModel,
    FieldInspectionModel,
    GovernmentReviewModel
)

# Table Name Constants
TABLE_USERS = "users"
TABLE_HOUSEHOLDS = "households"
TABLE_LOCATIONS = "locations"
TABLE_RESOURCES = "resources"
TABLE_DISASTER_REPORTS = "disaster_reports"
TABLE_RECOMMENDATIONS = "recommendations"
TABLE_DISASTERS = "disasters"
TABLE_ASSETS = "assets"
TABLE_ASSET_EVIDENCE = "asset_evidence"
TABLE_ASSET_VERIFICATIONS = "asset_verifications"
TABLE_ASSET_CERTIFICATES = "asset_certificates"
TABLE_DISASTER_CLAIMS = "disaster_claims"
TABLE_CLAIM_EVIDENCE = "claim_evidence"
TABLE_DAMAGE_ASSESSMENTS = "damage_assessments"
TABLE_VALUE_ASSESSMENTS = "value_assessments"
TABLE_FIELD_INSPECTIONS = "field_inspections"
TABLE_GOVERNMENT_REVIEWS = "government_reviews"
TABLE_ANOMALY_FLAGS = "anomaly_flags"
TABLE_AUDIT_EVENTS = "audit_events"
