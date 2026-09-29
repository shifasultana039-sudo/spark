from datetime import datetime, timezone, timedelta
from services.loss_assessment_engine import LossAssessmentEngine

def test_depreciation_calculation():
    engine = LossAssessmentEngine()
    
    # 2 years ago
    past_date = (datetime.now(timezone.utc) - timedelta(days=365*2)).isoformat()
    
    # original_value = 1000, category = electronics (rate = 0.20/yr), years = 2
    # expected depreciation = 1000 * (2 * 0.20) = 400
    depreciation = engine.calculate_depreciation(1000, past_date, "electronics")
    
    assert abs(depreciation - 400) < 10 # approximate check due to slight days diff

def test_loss_assessment_with_reference():
    engine = LossAssessmentEngine()
    past_date = (datetime.now(timezone.utc) - timedelta(days=365*2)).isoformat()
    
    result = engine.assess_loss(
        original_value=1000.0,
        purchase_date=past_date,
        asset_category="electronics",
        reference_value=500.0, # This is lower than depreciated value (1000 - 400 = 600)
        estimated_damage_percentage=50
    )
    
    assert result["label"] == "AI-ASSISTED ESTIMATE"
    assert "This is not a guaranteed compensation amount" in result["disclaimer"]
    
    # base_value used should be 500 (min of 600 and 500)
    # loss = 500 * 50% = 250
    assert abs(result["indicative_loss_estimate"] - 250.0) < 5
    
def test_loss_assessment_without_reference():
    engine = LossAssessmentEngine()
    past_date = (datetime.now(timezone.utc) - timedelta(days=365*2)).isoformat()
    
    result = engine.assess_loss(
        original_value=1000.0,
        purchase_date=past_date,
        asset_category="vehicle", # rate = 0.15/yr -> dep = 300
        reference_value=None, 
        estimated_damage_percentage=100
    )
    
    # base_value used should be depreciated value = 700
    # loss = 700 * 100% = 700
    assert abs(result["indicative_loss_estimate"] - 700.0) < 10
