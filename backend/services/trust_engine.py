"""
Transparent Trust Scoring Engine for ReliefChain AI.
Evaluates incoming field reports using explainable weighted factors.
"""

from typing import Dict, Any

SOURCE_SCORES = {
    "VERIFIED NGO": 25,
    "NGO": 25,
    "FIELD OFFICER": 25,
    "VERIFIED VOLUNTEER": 20,
    "VOLUNTEER": 20,
    "SATELLITE": 20,
    "SMS": 10,
    "SOCIAL MEDIA": 5,
    "UNKNOWN": 5
}

def calculate_trust_score(
    source: str,
    evidence_available: str,
    has_cross_confirmation: bool = False,
    is_recent: bool = True,
    is_contradictory: bool = False
) -> Dict[str, Any]:
    """
    Computes transparent multi-factor trust score (0 - 100):
    - Source reliability: Up to +25
    - Cross-source confirmation: +25
    - Evidence attached: +10
    - Recency: +10
    - Contradiction penalty: -20
    """
    src_clean = source.strip().upper()
    src_score = SOURCE_SCORES.get(src_clean, 10)
    
    conf_score = 25 if has_cross_confirmation else 0
    
    # Evidence score
    ev_score = 0
    if evidence_available and evidence_available.strip().lower() not in ["none", ""]:
        ev_score = 10
        
    rec_score = 10 if is_recent else 4
    penalty = -20 if is_contradictory else 0
    
    raw_score = src_score + conf_score + ev_score + rec_score + penalty
    final_trust = max(0, min(100, raw_score))
    
    # Verification status based on trust score
    if is_contradictory or final_trust < 50:
        status = "POTENTIALLY_INCONSISTENT"
    elif final_trust >= 80:
        status = "VERIFIED"
    else:
        status = "PENDING_VERIFICATION"
        
    return {
        "trust_score": final_trust,
        "source_reliability_score": src_score,
        "cross_confirmation_score": conf_score,
        "evidence_score": ev_score,
        "recency_score": rec_score,
        "consistency_penalty": penalty,
        "verification_status": status,
        "is_contradictory": 1 if is_contradictory else 0
    }
