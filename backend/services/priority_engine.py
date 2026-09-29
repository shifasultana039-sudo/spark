"""
AI Priority Engine and AI Safety Gate for ReliefChain AI.
Calculates transparent decision-support priority scores and enforces safety thresholds.
"""

from typing import Dict, Any

def calculate_priority_score(
    severity_score: int,       # 0 - 100
    population_score: int,     # 0 - 100
    shortage_score: int,       # 0 - 100
    trust_score: int,          # 0 - 100
    logistics_score: int       # 0 - 100
) -> Dict[str, Any]:
    """
    Computes weighted decision support priority score:
    - Severity: 30%
    - Population Impact: 25%
    - Resource Shortage: 20%
    - Trust / Confidence: 15%
    - Logistics / Accessibility: 10%
    """
    priority = (
        (severity_score * 0.30) +
        (population_score * 0.25) +
        (shortage_score * 0.20) +
        (trust_score * 0.15) +
        (logistics_score * 0.10)
    )
    final_priority = max(0, min(100, int(round(priority))))
    
    # AI Safety Gate Evaluation
    # Rule 1: 80 - 100 confidence -> AI recommendation can be generated.
    # Rule 2: 50 - 79 confidence  -> AI recommendation generated but "Human verification required".
    # Rule 3: 0 - 49 confidence   -> AI SAFETY HOLD triggered.
    if trust_score < 50:
        safety_status = "SAFETY_HOLD"
        safety_message = "🔴 AI SAFETY HOLD: Available evidence is insufficient or contradictory. Human verification is required before allocation."
        can_allocate = False
    elif trust_score < 80:
        safety_status = "HUMAN_VERIFICATION_REQUIRED"
        safety_message = "🟡 HUMAN VERIFICATION REQUIRED: Evidence confidence is moderate (50-79%). Human verification required before dispatch."
        can_allocate = True
    else:
        safety_status = "AUTONOMOUS_ELIGIBLE"
        safety_message = "🟢 HIGH CONFIDENCE: Evidence confidence exceeds 80%. AI recommendation generated for supervisor approval."
        can_allocate = True

    return {
        "priority_score": final_priority,
        "severity_score": severity_score,
        "population_score": population_score,
        "shortage_score": shortage_score,
        "trust_score": trust_score,
        "logistics_score": logistics_score,
        "safety_status": safety_status,
        "safety_message": safety_message,
        "can_allocate": can_allocate
    }
