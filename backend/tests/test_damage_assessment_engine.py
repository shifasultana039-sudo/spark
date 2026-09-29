import pytest
from services.damage_assessment_engine import DemoDamageAssessmentProvider

def test_demo_damage_assessment_provider():
    provider = DemoDamageAssessmentProvider()
    
    # Test major damage keyword
    result = provider.compare(
        asset_category="property",
        pre_evidence=[],
        post_evidence=[{"url": "post.jpg"}],
        citizen_description="the roof is gone"
    )
    assert result["damage_detected"] is True
    assert result["damage_category"] == "MAJOR_STRUCTURAL_DAMAGE"
    assert result["assessment_mode"] == "DEMO_SIMULATION"
    
    # Test moderate damage keyword
    result = provider.compare(
        asset_category="vehicle",
        pre_evidence=[],
        post_evidence=[{"url": "post.jpg"}],
        citizen_description="window is broken"
    )
    assert result["damage_detected"] is True
    assert result["damage_category"] == "MODERATE_DAMAGE"
    assert result["assessment_mode"] == "DEMO_SIMULATION"
    
    # Test minor/else keyword
    result = provider.compare(
        asset_category="electronics",
        pre_evidence=[],
        post_evidence=[{"url": "post.jpg"}],
        citizen_description="looks fine"
    )
    assert result["damage_detected"] is True
    assert result["damage_category"] == "MINOR_DAMAGE"
    assert result["assessment_mode"] == "DEMO_SIMULATION"

    # Test insufficient evidence
    result = provider.compare(
        asset_category="electronics",
        pre_evidence=[],
        post_evidence=[],
        citizen_description="just something"
    )
    assert result["damage_detected"] is False
    assert result["damage_category"] == "INSUFFICIENT_EVIDENCE"
    assert result["assessment_mode"] == "DEMO_SIMULATION"
