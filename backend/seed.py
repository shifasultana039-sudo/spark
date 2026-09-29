"""
ReliefChain AI - Complete Database Seeder
Seeds realistic simulated data for both Emergency Disaster Operations and the
Digital Asset Verification & Disaster Compensation Module.
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
try:
    from .database import get_db, init_db
    from .services.integrity_service import record_audit_event
    from .services.asset_verification_engine import generate_certificate_payload
except ImportError:
    from database import get_db, init_db
    from services.integrity_service import record_audit_event
    from services.asset_verification_engine import generate_certificate_payload

BASE_TIME = datetime(2026, 9, 28, 18, 0, 0, tzinfo=timezone.utc)

def seed_database():
    print("Initializing database tables...")
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # Clear existing data to avoid collision during re-seeding
        for tbl in ["users", "locations", "resources", "disaster_reports", "recommendations",
                    "disasters", "assets", "asset_evidence", "asset_certificates",
                    "disaster_claims", "claim_evidence", "damage_assessments",
                    "value_assessments", "field_inspections", "anomaly_flags", "audit_events"]:
            cursor.execute(f"DELETE FROM {tbl};")

        print("Seeding Users...")
        users = [
            ("USR-001", "Dr. Ananya Sharma", "ananya.sharma@reliefchain.org", "ADMIN", "Tamil Nadu Disaster Management Authority (TNDMA)", "0x742d35Cc6634C0532925a3b844Bc454e4438f44e", (BASE_TIME - timedelta(days=30)).isoformat()),
            ("USR-002", "Rajesh Kumar", "rajesh.k@redcross.org.in", "RELIEF_COORDINATOR", "Indian Red Cross Society - Vellore Chapter", "0x8a92B215E1D369Ac082f9bC488FeE3236e787f31", (BASE_TIME - timedelta(days=25)).isoformat()),
            ("USR-003", "Kavitha Sundaram", "kavitha.field@reliefvolunteers.in", "FIELD_VOLUNTEER", "Katpadi Youth Emergency Corps", "0x19B3dE73eF7c6d67bA215E9F90aA27718e268a7A", (BASE_TIME - timedelta(days=15)).isoformat()),
            ("USR-004", "Murugan Palanisamy", "murugan.logistics@tncivilsupplies.gov.in", "WAREHOUSE_MANAGER", "Vellore Central Food & Medical Depot", "0x53d6B1e81395b0606B1F374a491A25B951cD505D", (BASE_TIME - timedelta(days=20)).isoformat()),
            ("USR-005", "Public Viewer / Donor Portal", "public.audit@globalrelief.org", "VIEWER", "Transparent Aid Watch / Public Auditor", "0x0000000000000000000000000000000000000000", (BASE_TIME - timedelta(days=5)).isoformat()),
            ("USR-006", "Senthil Nathan (Citizen)", "senthil.n@citizen.tn.gov.in", "CITIZEN", "Katpadi Resident (HH-1001)", "0x91F5B46813A5C0532925a3b844Bc454e4438f99A", (BASE_TIME - timedelta(days=10)).isoformat()),
            ("USR-007", "Officer Rajesh V", "rajesh.revenue@vellore.tn.gov.in", "GOVERNMENT_OFFICER", "Vellore District Revenue & Relief Administration", "0x3D72B815E1D369Ac082f9bC488FeE3236e787c12", (BASE_TIME - timedelta(days=40)).isoformat())
        ]
        cursor.executemany("INSERT INTO users (user_id, name, email, role, organization, wallet_address, created_at) VALUES (?,?,?,?,?,?,?)", users)

        print("Seeding Locations (Tamil Nadu)...")
        locations = [
            ("Katpadi Relief Zone", "Vellore", "Tamil Nadu", 12.9806, 79.1417, 2400, "CRITICAL", "LIMITED_FLOODED", "CRITICAL", "HIGH", "MEDIUM", "HIGH", "Vellore Central Emergency Warehouse", 8.5, 32, 94, 91, "ACTIVE_DISASTER_ZONE"),
            ("Vellore Urban Emergency Zone", "Vellore", "Tamil Nadu", 12.9165, 79.1325, 4100, "HIGH", "PARTIAL_CLEAR", "HIGH", "CRITICAL", "HIGH", "MEDIUM", "Vellore Central Emergency Warehouse", 2.0, 12, 86, 88, "ACTIVE_DISASTER_ZONE"),
            ("Arcot Lowlands Relief Sector", "Ranipet", "Tamil Nadu", 12.9048, 79.3339, 2900, "HIGH", "MODERATE", "MEDIUM", "HIGH", "CRITICAL", "HIGH", "Ranipet District Logistics Depot", 7.2, 22, 79, 85, "ACTIVE_DISASTER_ZONE"),
            ("Ranipet Industrial Relief Hub", "Ranipet", "Tamil Nadu", 12.9272, 79.3331, 1850, "MEDIUM", "OPEN", "LOW", "MEDIUM", "HIGH", "LOW", "Ranipet District Logistics Depot", 4.1, 15, 67, 74, "MONITORED_ZONE"),
            ("Gudiyatham Western Valley", "Vellore", "Tamil Nadu", 12.9458, 78.8718, 1200, "LOW", "LANDSLIDE_RISK", "MEDIUM", "LOW", "MEDIUM", "LOW", "Vellore Central Emergency Warehouse", 34.0, 55, 58, 62, "INSPECTION_PENDING")
        ]
        cursor.executemany("""
        INSERT INTO locations (name, district, state, latitude, longitude, population_affected, severity,
                               accessibility, medical_shortage, water_shortage, food_shortage, shelter_shortage,
                               nearest_warehouse, distance_km, estimated_delivery_minutes, priority_score, trust_score, active_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, locations)

        print("Seeding Resources...")
        resources = [
            ("MEDICAL", "Emergency Trauma & First-Aid Medical Kits", "Kits", 2400, 500, 1200, "Vellore Central Emergency Warehouse", 300),
            ("WATER", "Clean Drinking Water Units (10L Sealed Packs)", "Packs", 8000, 2000, 4500, "Vellore Central Emergency Warehouse", 1000),
            ("FOOD", "Nutritional Ready-to-Eat Family Meal Packs", "Packages", 3200, 1200, 1800, "Ranipet District Logistics Depot", 500),
            ("SHELTER", "Waterproof Heavy-Duty Family Tents", "Units", 180, 150, 340, "Vellore Central Emergency Warehouse", 200),
            ("CLOTHING", "Emergency Dry Clothing & Thermal Blanket Kits", "Kits", 4460, 600, 400, "Ranipet District Logistics Depot", 400)
        ]
        cursor.executemany("""
        INSERT INTO resources (type, item_name, unit, available_quantity, reserved_quantity, dispatched_quantity, warehouse, critical_threshold)
        VALUES (?,?,?,?,?,?,?,?)
        """, resources)

        print("Seeding 48 Disaster Reports...")
        subzones = ["Junction North", "Bus Stand", "Riverbank", "Market Road", "Clinic Sector", "Lake View"]
        sources = [
            ("Verified NGO", 25, 25, 10, "Photo attached"),
            ("Field Officer", 25, 20, 10, "GPS inspection feed"),
            ("Verified Volunteer", 20, 20, 10, "Photo attached"),
            ("SMS", 10, 15, 0, "None"),
            ("Satellite", 20, 25, 10, "Thermal radar image"),
            ("Social Media", 5, 5, 0, "Unverified video")
        ]
        
        # Insert Anchor Report R-1042 (High priority cluster)
        cursor.execute("""
        INSERT INTO disaster_reports (report_id, source, location, sub_zone, latitude, longitude, description,
                                      people_affected, severity, required_resources, evidence_available, timestamp,
                                      trust_score, source_reliability_score, cross_confirmation_score, evidence_score,
                                      recency_score, consistency_penalty, verification_status, duplicate_cluster_id,
                                      is_contradictory, safety_gate_note, content_hash, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "R-1042", "Verified Volunteer", "Katpadi", "Katpadi Junction North", 12.9810, 79.1420,
            "Flood water has entered residential areas. Inundation up to 4 feet. Medical supplies are critically low.",
            2400, "CRITICAL", json.dumps(["Medical Kits", "Water Units", "Food Packages"]), "Photo attached (geotagged)",
            (BASE_TIME - timedelta(minutes=24)).isoformat(), 91, 20, 25, 10, 10, 0, "VERIFIED", "CLUSTER-KAT-01",
            0, "High confidence report backed by multiple sources.", "0x" + hashlib.sha256(b"R-1042").hexdigest(),
            (BASE_TIME - timedelta(minutes=24)).isoformat()
        ))

        # Anchor Report R-1028 (Contradiction / AI Safety Gate trigger)
        cursor.execute("""
        INSERT INTO disaster_reports (report_id, source, location, sub_zone, latitude, longitude, description,
                                      people_affected, severity, required_resources, evidence_available, timestamp,
                                      trust_score, source_reliability_score, cross_confirmation_score, evidence_score,
                                      recency_score, consistency_penalty, verification_status, duplicate_cluster_id,
                                      is_contradictory, safety_gate_note, content_hash, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "R-1028", "Social Media", "Gudiyatham", "Pernambut Road", 12.9460, 78.8720,
            "CATASTROPHIC DAM BREACH! Entire town washed away, 15,000 casualties! Need 10,000 trauma kits urgently!",
            15000, "CRITICAL", json.dumps(["Medical Kits", "Shelter Tents"]), "Unverified screenshot from 2021",
            (BASE_TIME - timedelta(minutes=15)).isoformat(), 32, 5, 0, 0, 10, -25, "POTENTIALLY_INCONSISTENT", "CONFLICT-GUD-01",
            1, "🔴 AI SAFETY HOLD: Available evidence is insufficient or contradictory. Human verification is required before allocation.",
            "0x" + hashlib.sha256(b"R-1028").hexdigest(), (BASE_TIME - timedelta(minutes=15)).isoformat()
        ))

        # Generate remaining 46 reports
        loc_names = ["Katpadi", "Vellore", "Arcot", "Ranipet", "Gudiyatham"]
        seen_r_ids = {"R-1042", "R-1028"}
        r_counter = 1001
        for idx in range(1, 47):
            while f"R-{r_counter}" in seen_r_ids:
                r_counter += 1
            r_id = f"R-{r_counter}"
            seen_r_ids.add(r_id)
            loc = loc_names[idx % len(loc_names)]
            src_info = sources[idx % len(sources)]
            sz = subzones[idx % len(subzones)]
            t_min = 10 + (idx * 5)
            rep_time = (BASE_TIME - timedelta(minutes=t_min)).isoformat()
            
            raw_trust = src_info[1] + src_info[2] + src_info[3] + 10
            is_conflict = 1 if (src_info[0] == "Social Media" and idx % 3 == 0) else 0
            if is_conflict:
                raw_trust -= 25
            trust = max(20, min(100, raw_trust))
            
            v_status = "POTENTIALLY_INCONSISTENT" if trust < 50 else ("VERIFIED" if trust >= 80 else "PENDING_VERIFICATION")
            cl_id = f"CLUSTER-{loc[:3].upper()}-01" if (idx % 2 == 0) else None

            cursor.execute("""
            INSERT INTO disaster_reports (report_id, source, location, sub_zone, latitude, longitude, description,
                                          people_affected, severity, required_resources, evidence_available, timestamp,
                                          trust_score, source_reliability_score, cross_confirmation_score, evidence_score,
                                          recency_score, consistency_penalty, verification_status, duplicate_cluster_id,
                                          is_contradictory, safety_gate_note, content_hash, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                r_id, src_info[0], loc, sz, 12.94 + (idx * 0.001), 79.13 + (idx * 0.002),
                f"[{sz}] Water stagnation and resource supply disruption reported in {loc}. Aid convoy requested.",
                400 + (idx * 50), "HIGH" if trust > 70 else "MEDIUM", json.dumps(["Water Units", "Food Packages"]),
                src_info[4], rep_time, trust, src_info[1], src_info[2], src_info[3], 10,
                -25 if is_conflict else 0, v_status, cl_id, is_conflict,
                "AI SAFETY HOLD: Flagged for field review" if trust < 50 else None,
                "0x" + hashlib.sha256(f"{r_id}|{loc}".encode()).hexdigest(), rep_time
            ))

        print("Seeding Recommendations (31 total: 27 on MST Blockchain)...")
        # Anchor recommendation RC-1042
        rec_hash = "0x" + hashlib.sha256(b"RC-1042|94|91|MEDICAL|400|BLOCKCHAIN_CONFIRMED").hexdigest()
        cursor.execute("""
        INSERT INTO recommendations (recommendation_id, location_id, location_name, primary_report_id,
                                     priority_score, confidence_score, resource_type, recommended_quantity,
                                     approved_quantity, explanation, severity_score, population_score, shortage_score,
                                     trust_score, logistics_score, alternative_considered, status, two_level_approval_required,
                                     approved_by_supervisor_1, approved_by_supervisor_2, human_override, override_reason,
                                     blockchain_tx_hash, block_number, approver_wallet, report_hash, created_at, approved_at, dispatched_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "RC-1042", 1, "Katpadi Relief Zone", "R-1042", 94, 91, "MEDICAL", 500, 400,
            "Katpadi was prioritized because it has a high severity level (95/100), approximately 2,400 affected residents, a critical medical shortage, and multiple independent reports. The reports have a 91% confidence score and nearby inventory is available at Vellore Central Warehouse (8.5 km).",
            95, 88, 92, 91, 80,
            json.dumps({"location_name": "Ranipet Relief Zone", "priority_score": 67, "rejection_reason": "Ranipet has lower report confidence and fewer independent confirmations."}),
            "BLOCKCHAIN_CONFIRMED", 1, "Dr. Ananya Sharma (TNDMA Admin)", "Rajesh Kumar (Relief Coordinator)", 1,
            "Secondary warehouse inventory is lower than originally reported; adjusted to 400 kits.",
            "0x8a92f03c15d487f918e7c65d3a1290bb8f3219aa4b726cf9381e05a8d9a47f31", 128456,
            "0x8a92B215E1D369Ac082f9bC488FeE3236e787f31", rec_hash,
            (BASE_TIME - timedelta(minutes=22)).isoformat(), (BASE_TIME - timedelta(minutes=18)).isoformat(),
            (BASE_TIME - timedelta(minutes=12)).isoformat()
        ))

        # Additional 30 recommendations
        for k in range(2, 32):
            rc_id = f"RC-{1000 + k}"
            loc_id = (k % 5) + 1
            loc_n = loc_names[k % len(loc_names)]
            is_bc = k <= 27
            tx_h = "0x" + hashlib.sha256(f"MST_{k}_{rc_id}".encode()).hexdigest() if is_bc else None
            status = "BLOCKCHAIN_CONFIRMED" if is_bc else ("BLOCKCHAIN_PENDING" if k <= 29 else "PENDING")

            cursor.execute("""
            INSERT INTO recommendations (recommendation_id, location_id, location_name, primary_report_id,
                                         priority_score, confidence_score, resource_type, recommended_quantity,
                                         approved_quantity, explanation, severity_score, population_score, shortage_score,
                                         trust_score, logistics_score, status, two_level_approval_required,
                                         approved_by_supervisor_1, approved_by_supervisor_2, human_override,
                                         blockchain_tx_hash, block_number, approver_wallet, report_hash, created_at, approved_at, dispatched_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                rc_id, loc_id, loc_n, f"R-{1000 + k}", 70 + (k % 25), 75 + (k % 20),
                "WATER" if k % 2 == 0 else "FOOD", 300 + (k * 20), 300 + (k * 20),
                f"Prioritized for {loc_n} relief sub-sector based on current resource index and corroborated volunteer logs.",
                75, 78, 80, 85, 70, status, 1 if k % 5 == 0 else 0,
                "Rajesh Kumar (Relief Coordinator)" if is_bc else None, None, 0,
                tx_h, 128456 + k if is_bc else None,
                "0x8a92B215E1D369Ac082f9bC488FeE3236e787f31" if is_bc else None,
                "0x" + hashlib.sha256(f"{rc_id}".encode()).hexdigest(),
                (BASE_TIME - timedelta(hours=k)).isoformat(),
                (BASE_TIME - timedelta(hours=k, minutes=-10)).isoformat() if is_bc else None,
                (BASE_TIME - timedelta(hours=k, minutes=-25)).isoformat() if is_bc else None
            ))

        print("Seeding Disasters Registry...")
        cursor.execute("""
        INSERT INTO disasters (disaster_code, name, disaster_type, state, district, severity, status, declared_at, description)
        VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            "DIS-2026-0007", "Tamil Nadu Monsoon Flash Flood (Simulation)", "FLOOD", "Tamil Nadu", "Vellore",
            "CRITICAL", "ACTIVE", (BASE_TIME - timedelta(days=2)).isoformat(),
            "Simulated cyclonic rainfall causing inundation of Palar river basin across Katpadi and Vellore."
        ))

        print("Seeding Citizen Assets & Evidence...")
        # Asset 1: House in Katpadi
        cert1 = generate_certificate_payload("AST-2026-000001", "HOUSE / PROPERTY", 94, "VERIFIED")
        cursor.execute("""
        INSERT INTO assets (asset_id, citizen_id, household_ref, category, description, documented_value,
                            purchase_date, location_address, latitude, longitude, status, verification_confidence,
                            certificate_token, qr_code_url, current_status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "AST-2026-000001", 6, "HH-1001", "HOUSE / PROPERTY", "Two-bedroom residential house with reinforced concrete roof",
            2500000.0, "2022-05-15", "14/2 Railway Feeder Road, Katpadi, Vellore, Tamil Nadu", 12.9810, 79.1420,
            "VERIFIED", 94, cert1["certificate_token"], cert1["verify_url"], "DAMAGED",
            (BASE_TIME - timedelta(days=60)).isoformat(), (BASE_TIME - timedelta(days=58)).isoformat()
        ))

        # Evidence for Asset 1
        ev_items = [
            ("EV-001", "AST-2026-000001", "GOVERNMENT_REGISTRATION", "/api/storage/uploads/demo_house_patta.jpg", "patta_property_registration.pdf", "0x5a19c3b8892f03c15d487f918e7c65d3a1290bb8f3219aa4b726cf9381e05a8d", 245000, "application/pdf", 30),
            ("EV-002", "AST-2026-000001", "PURCHASE_INVOICE", "/api/storage/uploads/demo_construction_bill.jpg", "construction_completion_certificate.pdf", "0x3e18a992b215e1d369ac082f9bc488fee3236e787f3119b3de73ef7c6d67ba21", 182000, "application/pdf", 25),
            ("EV-003", "AST-2026-000001", "TIMESTAMPED_PHOTO", "/api/storage/uploads/demo_pre_disaster_house.jpg", "pre_disaster_front_elevation.jpg", "0x7d6f5a3b844bc454e4438f44e19b3de73ef7c6d67ba215e9f90aa27718e268a7", 450000, "image/jpeg", 20),
            ("EV-004", "AST-2026-000001", "GEOLOCATION", "/api/storage/uploads/demo_gis_map.png", "tndma_survey_coordinates.png", "0x12a9bc488fee3236e787f3119b3de73ef7c6d67ba215e9f90aa27718e268a75a", 92000, "image/png", 10),
            ("EV-005", "AST-2026-000001", "PREVIOUS_INSPECTION", "/api/storage/uploads/demo_municipal_tax.pdf", "municipal_property_tax_receipt.pdf", "0x992b215e1d369ac082f9bc488fee3236e787f3119b3de73ef7c6d67ba215e9f", 110000, "application/pdf", 5),
            ("EV-006", "AST-2026-000001", "ASSESSOR_VERIFICATION", "/api/storage/uploads/demo_engineer_stamp.pdf", "licensed_structural_engineer_verification.pdf", "0x44bc454e4438f44e19b3de73ef7c6d67ba215e9f90aa27718e268a75a19c3b88", 160000, "application/pdf", 5)
        ]
        for ev in ev_items:
            cursor.execute("""
            INSERT INTO asset_evidence (evidence_id, asset_id, evidence_type, file_url, original_filename,
                                       sha256_hash, file_size, mime_type, uploader, verification_status,
                                       score_contribution, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ev[0], ev[1], ev[2], ev[3], ev[4], ev[5], ev[6], ev[7],
                "Senthil Nathan", "VERIFIED", ev[8], (BASE_TIME - timedelta(days=59)).isoformat()
            ))

        # Certificate for Asset 1
        cursor.execute("""
        INSERT INTO asset_certificates (certificate_id, asset_id, certificate_token, verification_status,
                                        evidence_confidence, evidence_hash, issued_at, qr_payload)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            cert1["certificate_id"], "AST-2026-000001", cert1["certificate_token"], "VERIFIED", 94,
            "0x5a19c3b8892f03c15d487f918e7c65d3a1290bb8f3219aa4b726cf9381e05a8d",
            (BASE_TIME - timedelta(days=58)).isoformat(), json.dumps(cert1["qr_payload"])
        ))

        # Asset 2: Motorcycle
        cert2 = generate_certificate_payload("AST-2026-000002", "VEHICLE", 94, "VERIFIED")
        cursor.execute("""
        INSERT INTO assets (asset_id, citizen_id, household_ref, category, description, documented_value,
                            purchase_date, location_address, latitude, longitude, status, verification_confidence,
                            certificate_token, qr_code_url, current_status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "AST-2026-000002", 6, "HH-1001", "VEHICLE", "150cc Commuter Motorcycle (TN 23 BK 4092)",
            110000.0, "2024-01-20", "14/2 Railway Feeder Road, Katpadi, Vellore, Tamil Nadu", 12.9810, 79.1420,
            "VERIFIED", 94, cert2["certificate_token"], cert2["verify_url"], "INTACT",
            (BASE_TIME - timedelta(days=45)).isoformat(), (BASE_TIME - timedelta(days=44)).isoformat()
        ))

        print("Seeding Disaster Claims & AI Damage Assessments...")
        # Claim 1: Filed for Asset 1 (House)
        cursor.execute("""
        INSERT INTO disaster_claims (claim_id, asset_id, household_ref, disaster_id, damage_description,
                                     pre_disaster_verification_status, review_status, officer_decision,
                                     created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            "CLM-2026-010291", "AST-2026-000001", "HH-1001", "DIS-2026-0007",
            "Severe flood water entered the house up to 4.2 feet. Cracks along exterior load-bearing walls, compound wall collapsed, silt water damaged flooring and interior fittings.",
            "VERIFIED", "UNDER_REVIEW", None, (BASE_TIME - timedelta(hours=6)).isoformat(), (BASE_TIME - timedelta(hours=4)).isoformat()
        ))

        # Post-disaster Claim Evidence
        cursor.execute("""
        INSERT INTO claim_evidence (evidence_id, claim_id, evidence_type, file_url, original_filename,
                                    sha256_hash, file_size, mime_type, captured_timestamp, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            "CLM-EV-001", "CLM-2026-010291", "POST_DISASTER_PHOTO", "/api/storage/uploads/demo_post_disaster_house.jpg",
            "post_disaster_inundation_watermark.jpg", "0x892f03c15d487f918e7c65d3a1290bb8f3219aa4b726cf9381e05a8d9a47f311",
            420000, "image/jpeg", (BASE_TIME - timedelta(hours=8)).isoformat(), (BASE_TIME - timedelta(hours=6)).isoformat()
        ))

        # AI Damage Assessment for Claim 1
        cursor.execute("""
        INSERT INTO damage_assessments (claim_id, damage_detected, damage_category, estimated_damage_percentage,
                                       asset_match_confidence, evidence_quality, overall_confidence, explanation,
                                       provider_name, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            "CLM-2026-010291", 1, "MAJOR_STRUCTURAL_DAMAGE", 70, 91, 87, 88,
            "Visible structural degradation detected on residential property. Pre-disaster reference shows intact load-bearing exterior walls. Post-disaster imagery demonstrates silt inundation up to 4.2 feet, moisture ingress, perimeter wall collapse, and exterior wall fissure patterns consistent with active monsoon flood exposure.",
            "DEMO_CV_MODEL", (BASE_TIME - timedelta(hours=5)).isoformat()
        ))

        # Indicative Value Assessment for Claim 1
        # Original: 2,500,000 -> Depreciation 8% (2 yrs at 4%) -> Reference: 2,300,000 -> 70% damage -> 1,610,000 loss
        cursor.execute("""
        INSERT INTO value_assessments (claim_id, original_documented_value, depreciation_percent, reference_current_value,
                                      estimated_damage_percentage, indicative_loss_amount, approved_compensation_amount,
                                      officer_notes, is_ai_assisted, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            "CLM-2026-010291", 2500000.0, 8.0, 2300000.0, 70, 1610000.0, None,
            "Awaiting officer review. Recommended for field surveyor inspection to verify foundation stability.",
            1, (BASE_TIME - timedelta(hours=5)).isoformat()
        ))

        # Field Inspection task
        cursor.execute("""
        INSERT INTO field_inspections (inspection_id, claim_id, assigned_officer, status, findings, damage_rating, created_at)
        VALUES (?,?,?,?,?,?,?)
        """, (
            "INSP-2026-0042", "CLM-2026-010291", "Kavitha Sundaram (Field Assessor)", "IN_PROGRESS",
            "Physical survey scheduled to verify water level gauge marks and concrete integrity.", "MAJOR_STRUCTURAL",
            (BASE_TIME - timedelta(hours=3)).isoformat()
        ))

        # Anomaly Flag for demo
        cursor.execute("""
        INSERT INTO anomaly_flags (entity_type, entity_id, flag_type, similarity_score, status, reason, created_at)
        VALUES (?,?,?,?,?,?,?)
        """, (
            "REPORT", "R-1028", "CONTRADICTION", 95, "REVIEW_REQUIRED",
            "Report claimed total dam breach with 15,000 casualties; contradicted by official irrigation sensor data showing 68% dam reservoir capacity.",
            (BASE_TIME - timedelta(minutes=14)).isoformat()
        ))

    print("Populating Tamper-Evident SHA-256 Audit Trail...")
    audit_chain = [
        ("System Gateway", "SYSTEM", "GENESIS", "SYSTEM", "CORE", "ReliefChain AI genesis state initialized."),
        ("Senthil Nathan", "CITIZEN", "ASSET_REGISTERED", "ASSET", "AST-2026-000001", "Citizen registered residential property at 14/2 Railway Feeder Road, Katpadi."),
        ("Senthil Nathan", "CITIZEN", "EVIDENCE_ADDED", "ASSET", "AST-2026-000001", "Uploaded Patta property title deed and pre-disaster photograph."),
        ("AI Trust Engine", "AI_SERVICE", "VERIFICATION_UPDATED", "ASSET", "AST-2026-000001", "Calculated verification confidence score: 94%. Status upgraded to VERIFIED."),
        ("ReliefChain Issuer", "SYSTEM", "CERTIFICATE_GENERATED", "ASSET", "AST-2026-000001", "Issued cryptographic Digital Asset Certificate with secure verification token."),
        ("TNDMA Alert Gateway", "ADMIN", "DISASTER_DECLARED", "DISASTER", "DIS-2026-0007", "Declared active emergency state for Tamil Nadu Monsoon Flash Flood."),
        ("Kavitha Sundaram", "FIELD_VOLUNTEER", "REPORT_RECEIVED", "REPORT", "R-1042", "Received critical flood report from Katpadi Junction residential zone."),
        ("AI Trust Engine", "AI_SERVICE", "TRUST_EVALUATED", "REPORT", "R-1042", "Assigned 91% trust score based on volunteer credentials and geotagged imagery."),
        ("AI Priority Engine", "AI_SERVICE", "PRIORITY_COMPUTED", "RECOMMENDATION", "RC-1042", "Priority score calculated at 94/100 for Katpadi relief zone."),
        ("AI Safety Gate", "AI_SERVICE", "SAFETY_GATE_PASSED", "RECOMMENDATION", "RC-1042", "Confidence 91% exceeds 80% autonomous threshold; requires Two-Level Human Approval due to large medical allocation."),
        ("Rajesh Kumar", "RELIEF_COORDINATOR", "HUMAN_OVERRIDE", "RECOMMENDATION", "RC-1042", "Supervisor adjusted allocation from 500 to 400 Medical Kits due to inventory buffer."),
        ("Dr. Ananya Sharma", "ADMIN", "HUMAN_APPROVAL_FINALIZED", "RECOMMENDATION", "RC-1042", "Executive second-tier approval signed with wallet 0x742d35Cc6634C0532925a3b844Bc454e4438f44e."),
        ("MST Blockchain Service", "BLOCKCHAIN", "MST_TX_SUBMITTED", "RECOMMENDATION", "RC-1042", "Submitted transaction to MST Testnet (Chain ID 88888). TX: 0x8a92f03c15d487f918e7c65d3a1290bb8f3219aa4b726cf9381e05a8d9a47f31"),
        ("MST Testnet Consensus", "BLOCKCHAIN", "MST_TX_CONFIRMED", "RECOMMENDATION", "RC-1042", "Block #128456 confirmed on MST Blockchain. Status: BLOCKCHAIN_CONFIRMED."),
        ("ReliefChain Verifier", "SYSTEM", "INTEGRITY_VERIFIED", "RECOMMENDATION", "RC-1042", "Cryptographic proof match: On-chain stored hash equals recalculated local decision hash."),
        ("Senthil Nathan", "CITIZEN", "CLAIM_CREATED", "CLAIM", "CLM-2026-010291", "Citizen submitted disaster damage claim for verified house AST-2026-000001."),
        ("Demo CV Model", "AI_SERVICE", "DAMAGE_ASSESSED", "CLAIM", "CLM-2026-010291", "AI comparison completed: Major structural damage detected (70% estimated loss)."),
        ("Value Engine", "AI_SERVICE", "VALUE_ESTIMATED", "CLAIM", "CLM-2026-010291", "Indicative loss estimated at ₹1,610,000 (Subject to government officer approval)."),
        ("Officer Rajesh V", "GOVERNMENT_OFFICER", "CLAIM_OPENED", "CLAIM", "CLM-2026-010291", "Government assessor opened claim dossier for formal review.")
    ]

    for item in audit_chain:
        record_audit_event(
            actor=item[0],
            role=item[1],
            event_type=item[2],
            entity_type=item[3],
            entity_id=item[4],
            description=item[5]
        )

    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
