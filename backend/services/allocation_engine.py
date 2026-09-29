"""
Resource Allocation Engine for ReliefChain AI.
Calculates needed relief quantities against live inventory constraints and critical thresholds.
"""

from typing import Dict, Any, List

def calculate_resource_allocation(
    resource_type: str,
    population_affected: int,
    severity: str,
    available_inventory: int,
    critical_threshold: int = 200
) -> Dict[str, Any]:
    """
    Computes required resources and checks against inventory availability.
    Enforces two-level approval for critical large-scale allocations.
    """
    sev_multiplier = 1.5 if severity == "CRITICAL" else (1.2 if severity == "HIGH" else 1.0)
    
    # Base estimation per resource type
    if resource_type == "MEDICAL":
        needed = int(round((population_affected * 0.20) * sev_multiplier))
    elif resource_type == "WATER":
        needed = int(round((population_affected * 0.40) * sev_multiplier))
    elif resource_type == "FOOD":
        needed = int(round((population_affected * 0.15) * sev_multiplier))
    elif resource_type == "SHELTER":
        needed = int(round((population_affected * 0.05) * sev_multiplier))
    else:
        needed = int(round((population_affected * 0.10) * sev_multiplier))
        
    needed = max(50, needed)
    
    # Inventory check
    has_constraint = False
    constraint_message = None
    recommended_qty = needed
    secondary_alternative = 0
    
    if needed > available_inventory:
        has_constraint = True
        recommended_qty = available_inventory
        secondary_alternative = needed - available_inventory
        constraint_message = (
            f"Resource Constraint: Only {available_inventory} units currently available. "
            f"Allocating {available_inventory} primary stock + recommending {secondary_alternative} from secondary depot."
        )

    # Two-level approval rule: if allocation is large (e.g. >400 medical kits or >1000 water units)
    two_level_required = (resource_type == "MEDICAL" and recommended_qty >= 400) or \
                         (resource_type == "WATER" and recommended_qty >= 1000) or \
                         (severity == "CRITICAL" and recommended_qty >= 300)

    return {
        "resource_type": resource_type,
        "needed_quantity": needed,
        "recommended_quantity": recommended_qty,
        "available_inventory": available_inventory,
        "has_constraint": has_constraint,
        "constraint_message": constraint_message,
        "secondary_alternative_recommended": secondary_alternative,
        "two_level_approval_required": two_level_required
    }
