"""
Deterministic Asset Evidence Verification Engine for ReliefChain AI.
Evaluates pre-disaster evidence, computes transparent and deterministic confidence scores (0-100),
generates natural language explanations, and maintains audit-ready scoring records.

Notice: This is a deterministic rule-based verification engine, not a trained AI model.
Every point in the confidence score is directly explainable and reproducible.
"""

import uuid
import secrets
from typing import List, Dict, Any, Optional

DEFAULT_EVIDENCE_WEIGHTS: Dict[str, int] = {
    "GOVERNMENT_REGISTRATION": 34,
    "PURCHASE_INVOICE": 25,
    "TIMESTAMPED_PHOTO": 20,
    "GEOLOCATION": 15,
    "PREVIOUS_INSPECTION": 5,
    "ASSESSOR_VERIFICATION": 5,
    "WARRANTY": 5,
    "WARRANTY_DOCUMENT": 5,
    "FIELD_INSPECTION_REPORT": 15,
    "FIELD_INSPECTION": 15,
    "POST_DISASTER_PHOTO": 10,
    "POST_DISASTER_VIDEO": 15,
    "OTHER": 5,
}

EVIDENCE_TYPE_ALIASES: Dict[str, str] = {
    "REGISTRATION": "GOVERNMENT_REGISTRATION",
    "GOVERNMENT_REGISTRATION": "GOVERNMENT_REGISTRATION",
    "REGISTRATION_DOCUMENT": "GOVERNMENT_REGISTRATION",
    "INVOICE": "PURCHASE_INVOICE",
    "PURCHASE_INVOICE": "PURCHASE_INVOICE",
    "PHOTO": "TIMESTAMPED_PHOTO",
    "TIMESTAMPED_PHOTO": "TIMESTAMPED_PHOTO",
    "TIMESTAMPED_PHOTOGRAPH": "TIMESTAMPED_PHOTO",
    "LOCATION": "GEOLOCATION",
    "GEOLOCATION": "GEOLOCATION",
    "LOCATION_EVIDENCE": "GEOLOCATION",
    "PREVIOUS_INSPECTION": "PREVIOUS_INSPECTION",
    "INSPECTION": "PREVIOUS_INSPECTION",
    "ASSESSOR_VERIFICATION": "ASSESSOR_VERIFICATION",
    "ASSESSOR": "ASSESSOR_VERIFICATION",
    "WARRANTY": "WARRANTY",
    "WARRANTY_DOCUMENT": "WARRANTY",
    "FIELD_INSPECTION": "FIELD_INSPECTION_REPORT",
    "FIELD_INSPECTION_REPORT": "FIELD_INSPECTION_REPORT",
    "INSPECTION_REPORT": "FIELD_INSPECTION_REPORT",
    "POST_DISASTER_PHOTO": "POST_DISASTER_PHOTO",
    "POST_DISASTER_VIDEO": "POST_DISASTER_VIDEO",
}

# Active configurable weights dictionary
ACTIVE_EVIDENCE_WEIGHTS: Dict[str, int] = dict(DEFAULT_EVIDENCE_WEIGHTS)

EVIDENCE_DISPLAY_NAMES: Dict[str, str] = {
    "GOVERNMENT_REGISTRATION": "Registration document",
    "PURCHASE_INVOICE": "Purchase invoice",
    "TIMESTAMPED_PHOTO": "Timestamped photograph",
    "GEOLOCATION": "Location evidence",
    "PREVIOUS_INSPECTION": "Previous inspection",
    "ASSESSOR_VERIFICATION": "Assessor verification",
    "WARRANTY": "Warranty document",
    "WARRANTY_DOCUMENT": "Warranty document",
    "FIELD_INSPECTION_REPORT": "Field inspection report",
    "FIELD_INSPECTION": "Field inspection report",
    "POST_DISASTER_PHOTO": "Post-disaster photograph",
    "POST_DISASTER_VIDEO": "Post-disaster video",
    "OTHER": "Supplemental documentation",
}


def get_evidence_weights() -> Dict[str, int]:
    """Returns a copy of the current active evidence weighting rules."""
    return dict(ACTIVE_EVIDENCE_WEIGHTS)


def configure_weights(new_weights: Dict[str, int]) -> Dict[str, int]:
    """Updates active evidence weighting rules for deterministic evaluation."""
    for k, v in new_weights.items():
        key_upper = k.strip().upper().replace(" ", "_").replace("/", "_").replace("-", "_")
        canonical_key = EVIDENCE_TYPE_ALIASES.get(key_upper, key_upper)
        if isinstance(v, (int, float)) and v >= 0:
            ACTIVE_EVIDENCE_WEIGHTS[canonical_key] = int(v)
            ACTIVE_EVIDENCE_WEIGHTS[key_upper] = int(v)
    return get_evidence_weights()


def reset_evidence_weights() -> Dict[str, int]:
    """Resets weighting rules back to default configuration."""
    global ACTIVE_EVIDENCE_WEIGHTS
    ACTIVE_EVIDENCE_WEIGHTS = dict(DEFAULT_EVIDENCE_WEIGHTS)
    return get_evidence_weights()


def generate_explanation(contributions: List[Dict[str, Any]]) -> str:
    """
    Generates human-readable natural language explanation matching the requested standard:
    e.g. 'Registration document, purchase invoice, timestamped photograph, and location evidence were available.'
    """
    if not contributions:
        return "No verifiable evidence documents have been submitted yet for this asset."

    names = [EVIDENCE_DISPLAY_NAMES.get(c["type"], c["type"].lower().replace("_", " ")) for c in contributions]
    
    # Capitalize first item
    first_name = names[0][0].upper() + names[0][1:]

    if len(names) == 1:
        return f"{first_name} was available."
    elif len(names) == 2:
        return f"{first_name} and {names[1].lower()} were available."
    else:
        middle_items = [n.lower() for n in names[1:-1]]
        last_item = names[-1].lower()
        items_str = ", ".join([first_name] + middle_items)
        return f"{items_str}, and {last_item} were available."


EVIDENCE_HIERARCHY: List[str] = [
    "GOVERNMENT_REGISTRATION",
    "PURCHASE_INVOICE",
    "TIMESTAMPED_PHOTO",
    "GEOLOCATION",
    "PREVIOUS_INSPECTION",
    "ASSESSOR_VERIFICATION",
    "WARRANTY",
    "FIELD_INSPECTION_REPORT",
    "POST_DISASTER_PHOTO",
    "POST_DISASTER_VIDEO",
    "OTHER",
]


def evaluate_asset_evidence(
    evidence_list: List[Dict[str, Any]],
    custom_weights: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Computes explainable and deterministic verification score based on uploaded proofs:
    - Never invents evidence. Only examines submitted items.
    - Configurable weights.
    - Confidence score strictly bounded between 0 and 100.
    - Assigns status:
        * OFFICIALLY_CONFIRMED: confidence >= 95
        * VERIFIED: 80 <= confidence < 95
        * PARTIALLY_VERIFIED: 50 <= confidence < 80
        * UNVERIFIED: confidence < 50
    """
    weights = dict(ACTIVE_EVIDENCE_WEIGHTS)
    if custom_weights:
        for k, v in custom_weights.items():
            key_upper = k.strip().upper().replace(" ", "_").replace("/", "_").replace("-", "_")
            canonical_key = EVIDENCE_TYPE_ALIASES.get(key_upper, key_upper)
            if isinstance(v, (int, float)) and v >= 0:
                weights[canonical_key] = int(v)
                weights[key_upper] = int(v)

    contributions = []
    seen_types = set()

    for item in evidence_list:
        raw_type = (item.get("evidence_type") or "").strip().upper().replace(" ", "_").replace("/", "_").replace("-", "_")
        canonical_type = EVIDENCE_TYPE_ALIASES.get(raw_type, raw_type)

        weight = weights.get(canonical_type, weights.get(raw_type, 5))

        # Ensure distinct evidence types contribute deterministically without double counting base score
        if canonical_type not in seen_types:
            seen_types.add(canonical_type)
            contributions.append({
                "type": canonical_type,
                "display_name": EVIDENCE_DISPLAY_NAMES.get(canonical_type, canonical_type),
                "weight": weight,
                "evidence_id": item.get("evidence_id", ""),
                "filename": item.get("original_filename", ""),
                "verified": True
            })

    # Sort contributions by canonical evidence hierarchy for deterministic presentation & explanation
    def get_priority(c: Dict[str, Any]) -> int:
        t = c.get("type", "")
        return EVIDENCE_HIERARCHY.index(t) if t in EVIDENCE_HIERARCHY else 999

    contributions.sort(key=get_priority)

    total_score = sum(c["weight"] for c in contributions)

    # Strict bounding 0–100
    confidence = min(100, max(0, total_score))

    # Deterministic status classification
    if confidence >= 95:
        verification_status = "OFFICIALLY_CONFIRMED"
    elif confidence >= 80:
        verification_status = "VERIFIED"
    elif confidence >= 50:
        verification_status = "PARTIALLY_VERIFIED"
    else:
        verification_status = "UNVERIFIED"

    explanation = generate_explanation(contributions)

    return {
        "confidence": confidence,
        "confidence_score": confidence,  # Backward compatibility
        "status": verification_status,
        "verification_status": verification_status,  # Backward compatibility
        "explanation": explanation,
        "contributions": contributions,
        "weights_used": weights,
        "is_deterministic": True,
        "engine_type": "DETERMINISTIC_RULES",
        "can_issue_certificate": confidence >= 80
    }


def generate_certificate_payload(asset_id: str, category: str, confidence: int, status: str) -> Dict[str, Any]:
    """
    Generates a secure verification token and safe QR code payload.
    Crucial Privacy Rule: QR MUST NOT expose private citizen names, phone numbers,
    exact home addresses, or private invoices.
    """
    secure_token = secrets.token_urlsafe(16)
    cert_id = f"CERT-2026-{uuid.uuid4().hex[:8].upper()}"

    qr_payload = {
        "certificate_id": cert_id,
        "asset_id": asset_id,
        "category": category,
        "verification_status": status,
        "evidence_confidence": f"{confidence}%",
        "verify_url": f"/verify/asset/{secure_token}"
    }

    return {
        "certificate_id": cert_id,
        "certificate_token": secure_token,
        "qr_payload": qr_payload,
        "verify_url": f"/verify/asset/{secure_token}"
    }
