"""
RELIEFCHAIN AI - FINAL COMPREHENSIVE 20-STEP END-TO-END WORKFLOW TEST

Validates the exact 20 steps requested by the user:
1. Login as Citizen
2. Create Asset
3. Upload Evidence
4. Verify Asset
5. Generate Certificate
6. Create Disaster Claim
7. Upload Post-Disaster Evidence
8. Run Demo AI Assessment
9. Generate Indicative Loss Estimate
10. Login as Government Officer
11. Open Claim
12. Review Evidence
13. Review AI Assessment
14. Review Anomalies
15. Review Audit Trail
16. Forward for Field Inspection
17. Login as NGO
18. Submit Inspection
19. Login as Government Officer
20. Complete Review Action
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CITIZEN_UID = "USR-006"        # Senthil Nathan (CITIZEN)
OFFICER_UID = "USR-007"        # Officer Rajesh V (GOVERNMENT_OFFICER)
NGO_UID = "USR-003"            # Kavitha Sundaram (FIELD_ASSESSOR / NGO)
DISASTER_ID = "DIS-2026-0007"  # Tamil Nadu Monsoon Flash Flood Simulation


def test_final_20_step_complete_workflow():
    print("\n--- STARTING 20-STEP E2E RELIEFCHAIN AI WORKFLOW ---")

    # =========================================================================
    # Step 1: Login as Citizen
    # =========================================================================
    res_login_cit = client.post("/api/auth/login", json={"user_id": CITIZEN_UID})
    assert res_login_cit.status_code == 200, f"Step 1 Failed: {res_login_cit.text}"
    cit_auth = res_login_cit.json()
    cit_token = cit_auth["access_token"]
    assert cit_token, "No access token returned for citizen"
    cit_headers = {"Authorization": f"Bearer {cit_token}"}
    print("Step 1: Logged in as Citizen (Senthil Nathan)")

    # =========================================================================
    # Step 2: Create Asset
    # =========================================================================
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "E2E Final Workflow Residential House",
            "documented_value": 2500000.0,
            "location_address": "42 Nehru Street, Katpadi, Vellore, Tamil Nadu",
            "household_ref": "HH-1001"
        },
        headers=cit_headers
    )
    assert res_asset.status_code == 201, f"Step 2 Failed: {res_asset.text}"
    asset = res_asset.json()
    asset_id = asset["asset_id"]
    assert asset_id.startswith("AST-")
    print(f"Step 2: Created Asset {asset_id}")

    # =========================================================================
    # Step 3: Upload Evidence (Pre-disaster baseline documents)
    # =========================================================================
    # Upload Government Registration proof (weight 34)
    reg_bytes = b"PDF_GOVERNMENT_REGISTRATION_DEED_PROOF"
    res_ev1 = client.post(
        f"/api/assets/{asset_id}/evidence",
        data={"evidence_type": "GOVERNMENT_REGISTRATION"},
        files={"file": ("title_deed.pdf", io.BytesIO(reg_bytes), "application/pdf")},
        headers=cit_headers
    )
    assert res_ev1.status_code == 201, f"Step 3A Failed: {res_ev1.text}"

    # Upload Purchase Invoice (weight 25)
    inv_bytes = b"PURCHASE_TAX_INVOICE_EVIDENCE"
    res_ev2 = client.post(
        f"/api/assets/{asset_id}/evidence",
        data={"evidence_type": "PURCHASE_INVOICE"},
        files={"file": ("tax_invoice.pdf", io.BytesIO(inv_bytes), "application/pdf")},
        headers=cit_headers
    )
    assert res_ev2.status_code == 201, f"Step 3B Failed: {res_ev2.text}"

    # Upload Timestamped Photograph (weight 20)
    photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00BASELINE_PHOTO"
    res_ev3 = client.post(
        f"/api/assets/{asset_id}/evidence",
        data={"evidence_type": "TIMESTAMPED_PHOTO"},
        files={"file": ("baseline_house.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers=cit_headers
    )
    assert res_ev3.status_code == 201, f"Step 3C Failed: {res_ev3.text}"

    # Upload Geolocation evidence (weight 15) -> Total weight: 34 + 25 + 20 + 15 = 94
    geo_bytes = b"GPS_GEOLOCATION_SURVEY_RECORD"
    res_ev4 = client.post(
        f"/api/assets/{asset_id}/evidence",
        data={"evidence_type": "GEOLOCATION"},
        files={"file": ("gps_survey.txt", io.BytesIO(geo_bytes), "text/plain")},
        headers=cit_headers
    )
    assert res_ev4.status_code == 201, f"Step 3D Failed: {res_ev4.text}"
    print(f"Step 3: Uploaded 4 pieces of baseline evidence for asset {asset_id}")

    # =========================================================================
    # Step 4: Verify Asset
    # =========================================================================
    res_verify = client.post(
        f"/api/assets/{asset_id}/verify",
        json={"evaluator_note": "Automated deterministic pre-disaster verification"},
        headers=cit_headers
    )
    assert res_verify.status_code == 200, f"Step 4 Failed: {res_verify.text}"
    v_data = res_verify.json()
    assert v_data["confidence"] >= 80, f"Expected confidence >= 80, got {v_data['confidence']}"
    assert v_data["status"] in ("VERIFIED", "OFFICIALLY_CONFIRMED")
    print(f"Step 4: Asset {asset_id} verified with confidence {v_data['confidence']}%")

    # =========================================================================
    # Step 5: Generate Certificate
    # =========================================================================
    res_cert = client.post(f"/api/assets/{asset_id}/certificate", headers=cit_headers)
    assert res_cert.status_code in (200, 201), f"Step 5 Failed: {res_cert.text}"
    cert_data = res_cert.json()
    assert "certificate_id" in cert_data or "certificate_token" in cert_data
    cert_id = cert_data.get("certificate_id") or cert_data.get("certificate_token")
    print(f"Step 5: Safe Asset Certificate generated: {cert_id}")

    # =========================================================================
    # Step 6: Create Disaster Claim
    # =========================================================================
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flash flood submerged ground floor up to 4 feet; front veranda boundary wall partially collapsed.",
            "household_ref": "HH-1001"
        },
        headers=cit_headers
    )
    assert res_claim.status_code == 201, f"Step 6 Failed: {res_claim.text}"
    claim = res_claim.json()
    claim_id = claim["claim_id"]
    assert claim_id.startswith("CLM-")
    print(f"Step 6: Created Disaster Claim {claim_id}")

    # =========================================================================
    # Step 7: Upload Post-Disaster Evidence
    # =========================================================================
    post_flood_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00POST_FLOOD_DAMAGE_SURVEY"
    res_claim_ev = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("post_disaster_flood.jpg", io.BytesIO(post_flood_bytes), "image/jpeg")},
        headers=cit_headers
    )
    assert res_claim_ev.status_code == 201, f"Step 7 Failed: {res_claim_ev.text}"
    claim_ev = res_claim_ev.json()
    assert "EV-" in claim_ev["evidence_id"]
    print(f"Step 7: Uploaded post-disaster evidence {claim_ev['evidence_id']}")

    # =========================================================================
    # Step 8: Run Demo AI Assessment
    # =========================================================================
    res_assess = client.post(f"/api/claims/{claim_id}/assess", headers=cit_headers)
    assert res_assess.status_code in (200, 201), f"Step 8 Failed: {res_assess.text}"
    assess_data = res_assess.json()
    assert "estimated_damage_percentage" in assess_data or "damage_percentage" in assess_data
    damage_pct = assess_data.get("estimated_damage_percentage") or assess_data.get("damage_percentage")
    print(f"Step 8: AI Assessment evaluated damage at {damage_pct}%")

    # =========================================================================
    # Step 9: Generate Indicative Loss Estimate
    # =========================================================================
    res_loss = client.post(f"/api/claims/{claim_id}/loss-estimate", headers=cit_headers)
    assert res_loss.status_code == 200, f"Step 9 Failed: {res_loss.text}"
    loss_data = res_loss.json()
    indicative_loss = loss_data["indicative_loss_estimate"]
    assert indicative_loss > 0
    print(f"Step 9: Indicative loss estimate generated: INR {indicative_loss:,.2f}")

    # =========================================================================
    # Step 10: Login as Government Officer
    # =========================================================================
    res_login_off = client.post("/api/auth/login", json={"user_id": OFFICER_UID})
    assert res_login_off.status_code == 200, f"Step 10 Failed: {res_login_off.text}"
    off_auth = res_login_off.json()
    off_token = off_auth["access_token"]
    off_headers = {"Authorization": f"Bearer {off_token}"}
    print("Step 10: Logged in as Government Officer (Officer Rajesh V)")

    # =========================================================================
    # Step 11: Open Claim
    # =========================================================================
    res_get_claim = client.get(f"/api/claims/{claim_id}", headers=off_headers)
    assert res_get_claim.status_code == 200, f"Step 11 Failed: {res_get_claim.text}"
    opened_claim = res_get_claim.json()
    assert opened_claim["claim_id"] == claim_id
    print(f"Step 11: Opened claim dossier for {claim_id}")

    # =========================================================================
    # Step 12: Review Evidence
    # =========================================================================
    res_post_ev = client.get(f"/api/claims/{claim_id}/evidence", headers=off_headers)
    assert res_post_ev.status_code == 200
    assert len(res_post_ev.json()) >= 1

    res_pre_ev = client.get(f"/api/assets/{asset_id}/evidence", headers=off_headers)
    assert res_pre_ev.status_code == 200
    assert len(res_pre_ev.json()) >= 4
    print(f"Step 12: Reviewed pre-disaster ({len(res_pre_ev.json())}) & post-disaster ({len(res_post_ev.json())}) evidence")

    # =========================================================================
    # Step 13: Review AI Assessment
    # =========================================================================
    res_get_assess = client.get(f"/api/claims/{claim_id}/assessment", headers=off_headers)
    assert res_get_assess.status_code == 200
    assert res_get_assess.json() is not None
    print("Step 13: Reviewed AI Damage Assessment data")

    # =========================================================================
    # Step 14: Review Anomalies
    # =========================================================================
    res_anomalies = client.get(f"/api/claims/{claim_id}/anomalies", headers=off_headers)
    assert res_anomalies.status_code == 200
    anomalies_data = res_anomalies.json()
    assert "total_anomalies" in anomalies_data
    # Verify non-accusatory language
    assert "fraudulent" not in res_anomalies.text.lower()
    print(f"Step 14: Reviewed anomalies (Total flags: {anomalies_data['total_anomalies']})")

    # =========================================================================
    # Step 15: Review Audit Trail
    # =========================================================================
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers=off_headers)
    assert res_audit.status_code == 200
    audit_events = res_audit.json()
    assert len(audit_events) >= 3
    print(f"Step 15: Reviewed sequential audit trail ({len(audit_events)} events)")

    # =========================================================================
    # Step 16: Forward for Field Inspection
    # =========================================================================
    res_fwd = client.post(
        f"/api/claims/{claim_id}/forward-inspection",
        json={
            "inspection_sector": "Katpadi Sector 3",
            "assigned_inspector_id": "Kavitha Sundaram (NGO Volunteer)",
            "special_instructions": "Verify boundary wall damage and flood height level mark."
        },
        headers=off_headers
    )
    assert res_fwd.status_code == 200, f"Step 16 Failed: {res_fwd.text}"
    fwd_claim = res_fwd.json()
    assert fwd_claim["review_status"] == "FIELD_INSPECTION_PENDING"
    print("Step 16: Forwarded claim for field inspection")

    # =========================================================================
    # Step 17: Login as NGO
    # =========================================================================
    res_login_ngo = client.post("/api/auth/login", json={"user_id": NGO_UID})
    assert res_login_ngo.status_code == 200, f"Step 17 Failed: {res_login_ngo.text}"
    ngo_auth = res_login_ngo.json()
    ngo_token = ngo_auth["access_token"]
    ngo_headers = {"Authorization": f"Bearer {ngo_token}"}
    print("Step 17: Logged in as NGO Field Assessor (Kavitha Sundaram)")

    # =========================================================================
    # Step 18: Submit Inspection
    # =========================================================================
    # Fetch assigned inspection
    res_insp_list = client.get(f"/api/inspections?claim_id={claim_id}", headers=ngo_headers)
    assert res_insp_list.status_code == 200
    insps = res_insp_list.json()
    assert len(insps) >= 1
    insp_id = insps[0]["inspection_id"]

    # 1. Add findings
    res_find = client.post(
        f"/api/inspections/{insp_id}/findings",
        json={
            "field_findings": "Physical ground verification completed. Boundary wall collapsed 8m length. Living area shows 3.8ft watermark.",
            "damage_severity_rating": "MODERATE_DAMAGE"
        },
        headers=ngo_headers
    )
    assert res_find.status_code == 200

    # 2. Upload survey evidence
    survey_photo = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00OFFICIAL_NGO_SURVEY"
    res_up_insp = client.post(
        f"/api/inspections/{insp_id}/evidence",
        data={"evidence_type": "FIELD_PHOTO"},
        files={"file": ("ngo_ground_survey.jpg", io.BytesIO(survey_photo), "image/jpeg")},
        headers=ngo_headers
    )
    assert res_up_insp.status_code == 200

    # 3. Submit inspection report
    res_sub_insp = client.post(
        f"/api/inspections/{insp_id}/submit",
        json={
            "field_findings": "Final report: Structural integrity sound. Plaster repair and boundary wall reconstruction recommended.",
            "damage_severity_rating": "MODERATE_DAMAGE"
        },
        headers=ngo_headers
    )
    assert res_sub_insp.status_code == 200
    sub_detail = res_sub_insp.json()
    assert sub_detail["status"] == "COMPLETED"
    print(f"Step 18: NGO submitted official field inspection report for {insp_id}")

    # =========================================================================
    # Step 19: Login as Government Officer
    # =========================================================================
    res_login_off2 = client.post("/api/auth/login", json={"user_id": OFFICER_UID})
    assert res_login_off2.status_code == 200
    off_headers2 = {"Authorization": f"Bearer {res_login_off2.json()['access_token']}"}

    # Verify officer can view submitted inspection report
    res_gov_insp = client.get(f"/api/claims/{claim_id}/inspection", headers=off_headers2)
    assert res_gov_insp.status_code == 200
    gov_insp = res_gov_insp.json()
    assert gov_insp["status"] == "COMPLETED"
    assert "Final report" in gov_insp["findings"]
    print(f"Step 19: Government Officer verified completed field inspection report")

    # =========================================================================
    # Step 20: Complete Review Action (Approve claim)
    # =========================================================================
    res_approve = client.post(
        f"/api/claims/{claim_id}/approve",
        json={
            "approved_amount": indicative_loss,
            "notes": "Claim finalized and approved after verified baseline asset, damage CV assessment, and completed NGO field survey."
        },
        headers=off_headers2
    )
    assert res_approve.status_code == 200, f"Step 20 Failed: {res_approve.text}"
    approved_claim = res_approve.json()
    assert approved_claim["review_status"] == "APPROVED"
    assert approved_claim["approved_compensation_amount"] == indicative_loss
    print(f"Step 20: Government Officer completed review action: APPROVED with INR {indicative_loss:,.2f}")

    print("\n--- ALL 20 WORKFLOW STEPS COMPLETED & VERIFIED 100% SUCCESSFULLY ---")
