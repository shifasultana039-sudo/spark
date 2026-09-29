"""
Explainable AI Decision Engine for ReliefChain AI.
Produces human-understandable reasoning and counterfactual alternative comparisons.
"""

from typing import Dict, Any

def generate_decision_explanation(
    location_name: str,
    severity: str,
    population_affected: int,
    shortage_type: str,
    trust_score: int,
    warehouse_distance_km: float,
    alternative_location: str,
    alternative_priority: int,
    alternative_reason: str
) -> Dict[str, Any]:
    """
    Builds structured explainability payload answering:
    1. Why was this location prioritized?
    2. What alternative location was evaluated and why was it not selected first?
    """
    reasoning = (
        f"{location_name} was prioritized because it exhibits a {severity.lower()} severity level, "
        f"approximately {population_affected:,} affected residents, a critical {shortage_type.lower()} shortage, "
        f"and multiple corroborated field reports. The evidence stream holds a {trust_score}% confidence score, "
        f"and nearest stock is positioned {warehouse_distance_km} km away."
    )
    
    return {
        "primary_reasoning": reasoning,
        "alternative_considered": {
            "location_name": alternative_location,
            "priority_score": alternative_priority,
            "rejection_reason": alternative_reason
        }
    }
