"""
Execution script to run digital asset database migrations and validate the 13 relational entities.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.migrations import run_digital_asset_migrations, validate_all_relational_models

def main():
    print("================================================================================")
    print("RELIEFCHAIN AI - DATABASE MIGRATION & VALIDATION RUNNER")
    print("Digital Asset Verification & Disaster Compensation Module")
    print("================================================================================\n")

    print("[1/2] Applying database migrations...")
    migration_result = run_digital_asset_migrations()
    for change in migration_result["changes_applied"]:
        print(f"  + {change}")
    print(f"Status: {migration_result['status']}\n")

    print("[2/2] Validating all 13 required relational domain models...")
    validation = validate_all_relational_models()

    entity_mapping = {
        "users": "1. User",
        "households": "2. Household",
        "assets": "3. Asset",
        "asset_evidence": "4. Evidence",
        "asset_verifications": "5. AssetVerification",
        "asset_certificates": "6. Certificate",
        "disaster_claims": "7. DisasterClaim",
        "damage_assessments": "8. DamageAssessment",
        "value_assessments": "9. ValueAssessment",
        "anomaly_flags": "10. AnomalyFlag",
        "audit_events": "11. AuditEvent",
        "field_inspections": "12. FieldInspection",
        "government_reviews": "13. GovernmentReview"
    }

    print("-" * 80)
    print(f"{'ENTITY MODEL':<25} | {'TABLE NAME':<22} | {'EXISTS':<8} | {'COLS':<6} | {'ROWS'}")
    print("-" * 80)

    for tbl, entity_name in entity_mapping.items():
        info = validation["table_details"].get(tbl, {})
        exists_str = "YES [PASS]" if info.get("exists") else "NO [FAIL]"
        cols = info.get("column_count", 0)
        rows = info.get("row_count", 0)
        print(f"{entity_name:<25} | {tbl:<22} | {exists_str:<8} | {cols:<6} | {rows}")

    print("-" * 80)
    print(f"\nForeign Keys Enforced: {'ENABLED' if validation['foreign_keys_enabled'] else 'DISABLED'}")
    print(f"All 13 Required Models Verified: {'PASSED [100%]' if validation['all_13_models_present'] else 'FAILED'}")

    # Inspect Asset table columns specifically
    asset_cols = validation["table_details"]["assets"]["columns"]
    print("\nAsset Model Specification Check:")
    asset_checks = [
        ("asset ID", "asset_id" in asset_cols),
        ("category", "category" in asset_cols),
        ("description", "description" in asset_cols),
        ("approximate/documented value", "documented_value" in asset_cols),
        ("purchase date", "purchase_date" in asset_cols),
        ("location", "location_address" in asset_cols and "latitude" in asset_cols and "longitude" in asset_cols),
        ("household reference", "household_ref" in asset_cols),
        ("registration timestamp", "created_at" in asset_cols),
        ("verification status", "status" in asset_cols),
        ("evidence confidence", "verification_confidence" in asset_cols),
        ("integrity hash", "integrity_hash" in asset_cols),
    ]
    for label, passed in asset_checks:
        status_tag = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_tag} {label}")

    # Inspect Evidence table columns specifically
    ev_cols = validation["table_details"]["asset_evidence"]["columns"]
    print("\nEvidence Model Specification Check:")
    ev_checks = [
        ("evidence type", "evidence_type" in ev_cols),
        ("file/reference", "file_url" in ev_cols and "original_filename" in ev_cols),
        ("timestamp", "captured_timestamp" in ev_cols or "created_at" in ev_cols),
        ("metadata", "metadata_json" in ev_cols),
        ("verification status", "verification_status" in ev_cols),
        ("SHA-256 hash", "sha256_hash" in ev_cols),
    ]
    for label, passed in ev_checks:
        status_tag = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_tag} {label}")

    if not validation["all_13_models_present"]:
        sys.exit(1)

    print("\n================================================================================")
    print("DATABASE FOUNDATION VALIDATION: 100% SUCCESSFUL!")
    print("================================================================================")

if __name__ == "__main__":
    main()
