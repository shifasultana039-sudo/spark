"""
Duplicate and Anomaly Detection Engine for ReliefChain AI.
Detects clustered reports and conflicts without making accusations.
"""

from typing import List, Dict, Any, Optional

def analyze_report_cluster(
    new_report_desc: str,
    location: str,
    existing_reports: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates whether an incoming report belongs to an existing incident cluster
    or conflicts with verified field observations.
    """
    matched_cluster = None
    is_conflicting = False
    conflict_reason = None
    
    loc_clean = location.strip().lower()
    desc_words = set(new_report_desc.lower().split())
    
    for rep in existing_reports:
        if rep.get("location", "").strip().lower() == loc_clean:
            # Check description word overlap
            rep_words = set(rep.get("description", "").lower().split())
            overlap = desc_words.intersection(rep_words)
            
            # Substantial overlap suggests same incident cluster
            if len(overlap) >= 3:
                matched_cluster = rep.get("duplicate_cluster_id") or f"CLUSTER-{location[:3].upper()}-01"
                
            # Conflict check: e.g. severe disaster reported vs verified low/normal
            if "dam breach" in new_report_desc.lower() and "normal" in rep.get("description", "").lower():
                is_conflicting = True
                conflict_reason = "Report severely contradicts on-site inspection telemetry. Human verification required."

    return {
        "is_duplicate_cluster": matched_cluster is not None,
        "duplicate_cluster_id": matched_cluster,
        "is_conflicting": is_conflicting,
        "conflict_reason": conflict_reason,
        "status_label": "Potentially inconsistent report" if is_conflicting else ("Cluster matched" if matched_cluster else "Unique report")
    }
