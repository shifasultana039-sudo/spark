"""
Value Assessment Engine for Disaster Claims.
Computes reference current value, depreciation, and indicative loss estimates.
Crucial Rule: AI estimates are NEVER guaranteed compensation.
"""

from datetime import datetime
from typing import Dict, Any

DEPRECIATION_RULES = {
    "HOUSE / PROPERTY": {"annual_rate": 0.04, "max_depreciation": 0.35},
    "PROPERTY": {"annual_rate": 0.04, "max_depreciation": 0.35},
    "VEHICLE": {"annual_rate": 0.12, "max_depreciation": 0.65},
    "AGRICULTURAL EQUIPMENT": {"annual_rate": 0.10, "max_depreciation": 0.50},
    "ELECTRONICS": {"annual_rate": 0.20, "max_depreciation": 0.75},
    "HOUSEHOLD APPLIANCE": {"annual_rate": 0.15, "max_depreciation": 0.70},
    "LIVESTOCK": {"annual_rate": 0.05, "max_depreciation": 0.40},
    "BUSINESS EQUIPMENT": {"annual_rate": 0.12, "max_depreciation": 0.60},
    "OTHER": {"annual_rate": 0.10, "max_depreciation": 0.50}
}

DISCLAIMER_TEXT = (
    "AI-assisted estimate — Final compensation is subject to government verification, "
    "applicable disaster relief norms, and authorized officer approval."
)

def compute_indicative_loss(
    original_value: float,
    purchase_date_str: str,
    category: str,
    damage_percentage: int
) -> Dict[str, Any]:
    """
    Calculates reference current value after depreciation, then applies estimated damage %
    to calculate indicative financial loss.
    """
    rule = DEPRECIATION_RULES.get(category.strip().upper(), DEPRECIATION_RULES["OTHER"])
    
    # Calculate age in years
    years_old = 1.0
    if purchase_date_str:
        try:
            p_date = datetime.strptime(purchase_date_str.split("T")[0], "%Y-%m-%d")
            delta = datetime.now() - p_date
            years_old = max(0.5, delta.days / 365.25)
        except Exception:
            years_old = 1.5

    accumulated_depreciation = min(rule["max_depreciation"], years_old * rule["annual_rate"])
    reference_current_value = round(original_value * (1.0 - accumulated_depreciation), 2)
    
    # Indicative loss amount
    indicative_loss = round(reference_current_value * (damage_percentage / 100.0), 2)

    return {
        "original_documented_value": original_value,
        "depreciation_percent": round(accumulated_depreciation * 100, 1),
        "reference_current_value": reference_current_value,
        "estimated_damage_percentage": damage_percentage,
        "indicative_loss_amount": indicative_loss,
        "disclaimer": DISCLAIMER_TEXT,
        "is_ai_assisted": True
    }
