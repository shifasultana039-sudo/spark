from typing import Dict, Any, Optional
from datetime import datetime, timezone

class LossAssessmentEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Default depreciation rules
        # Format: {"category": {"method": "linear", "rate_per_year": 0.1, "max_depreciation": 0.8}}
        self.depreciation_rules = {
            "electronics": {"method": "linear", "rate_per_year": 0.20, "max_depreciation": 0.9},
            "vehicle": {"method": "linear", "rate_per_year": 0.15, "max_depreciation": 0.8},
            "property": {"method": "linear", "rate_per_year": 0.02, "max_depreciation": 0.5},
            "default": {"method": "linear", "rate_per_year": 0.10, "max_depreciation": 0.75}
        }
        
        if config and "depreciation_rules" in config:
            self.depreciation_rules.update(config["depreciation_rules"])
            
    def calculate_depreciation(self, original_value: float, purchase_date: str, category: str) -> float:
        """Calculates depreciation based on rules and time elapsed."""
        try:
            purchase_dt = datetime.fromisoformat(purchase_date.replace("Z", "+00:00"))
            if purchase_dt.tzinfo is None:
                purchase_dt = purchase_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # If invalid date, assume 0 depreciation or use a fallback. We'll use 0.
            return 0.0
            
        now = datetime.now(timezone.utc)
        
        # Calculate years difference approximately
        days_elapsed = (now - purchase_dt).days
        years_elapsed = days_elapsed / 365.25
        
        if years_elapsed < 0:
            return 0.0
            
        rule = self.depreciation_rules.get(category.lower(), self.depreciation_rules["default"])
        
        rate = rule.get("rate_per_year", 0.1)
        max_dep = rule.get("max_depreciation", 0.8)
        
        # Linear depreciation
        depreciation_factor = min(years_elapsed * rate, max_dep)
        
        return original_value * depreciation_factor

    def assess_loss(
        self,
        original_value: float,
        purchase_date: str,
        asset_category: str,
        reference_value: Optional[float],
        estimated_damage_percentage: int
    ) -> Dict[str, Any]:
        """
        Calculates indicative loss estimate.
        """
        # Calculate depreciation
        depreciation = self.calculate_depreciation(original_value, purchase_date, asset_category)
        
        # Current value after depreciation
        depreciated_value = original_value - depreciation
        
        # Determine base value to use for loss calculation
        # If reference_value is provided, it might override or inform the value.
        # For this implementation, we take the minimum of depreciated_value and reference_value if provided.
        base_value = depreciated_value
        if reference_value is not None:
            base_value = min(depreciated_value, reference_value)
            
        # Calculate indicative loss
        damage_fraction = estimated_damage_percentage / 100.0
        indicative_loss = base_value * damage_fraction
        
        # Round values for display
        depreciation_rounded = round(depreciation, 2)
        base_value_rounded = round(base_value, 2)
        indicative_loss_rounded = round(indicative_loss, 2)
        
        explanation = (
            f"Calculated based on original value {original_value}, "
            f"depreciated by {depreciation_rounded} over time. "
            f"Applied damage percentage of {estimated_damage_percentage}%. "
            f"Base value used: {base_value_rounded}."
        )
        
        return {
            "label": "AI-ASSISTED ESTIMATE",
            "disclaimer": "This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules.",
            "original_documented_value": original_value,
            "reference_current_value": reference_value if reference_value is not None else depreciated_value,
            "depreciation": depreciation_rounded,
            "damage_percentage": estimated_damage_percentage,
            "indicative_loss_estimate": indicative_loss_rounded,
            "calculation_explanation": explanation
        }

loss_engine = LossAssessmentEngine()
