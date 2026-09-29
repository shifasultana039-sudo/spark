from typing import Optional
from pydantic import BaseModel, Field

class DamageAssessmentResponse(BaseModel):
    id: Optional[int] = None
    claim_id: str
    damage_detected: bool
    damage_category: str
    estimated_damage_percentage: int
    damage_percentage: Optional[float] = None
    asset_match_confidence: int
    evidence_quality: int
    overall_confidence: int
    explanation: str
    provider_name: str
    assessment_mode: str
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class LossAssessmentRequest(BaseModel):
    reference_value: Optional[float] = None
    estimated_damage_percentage: Optional[int] = None

class LossAssessmentResponse(BaseModel):
    label: str = Field(default="AI-ASSISTED ESTIMATE")
    disclaimer: str = Field(default="This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules.")
    original_documented_value: float
    original_value: Optional[float] = None
    reference_current_value: float
    depreciation: float
    damage_percentage: int
    indicative_loss_estimate: float
    indicative_loss_amount: Optional[float] = None
    calculation_explanation: str

    def __init__(self, **data):
        super().__init__(**data)
        if self.original_value is None:
            self.original_value = self.original_documented_value
        if self.indicative_loss_amount is None:
            self.indicative_loss_amount = self.indicative_loss_estimate

