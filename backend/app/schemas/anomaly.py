"""
ReliefChain AI — Anomaly Flag Schemas (Step 16).

Defines request/response shapes for  GET /claims/{claim_id}/anomalies.

IMPORTANT: No field is named 'fraudulent' or 'fraud'.
All flags carry  review_status = REVIEW_REQUIRED  to preserve citizen dignity
while alerting officers to discrepancies that warrant human verification.
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AnomalyFlagResponse(BaseModel):
    """
    A single anomaly flag associated with a disaster claim.

    Step 16 specification fields:
    - type (and flag_type for compatibility)
    - reason
    - confidence / similarity (and similarity_score for compatibility)
    - related_record
    - created_timestamp (and created_at for compatibility)
    - review_status (always REVIEW_REQUIRED)
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[int] = None
    entity_type: str = "CLAIM"
    entity_id: str
    flag_type: str
    type: Optional[str] = None
    reason: str
    similarity_score: int = 100
    similarity: Optional[int] = None
    confidence: Optional[int] = None
    review_status: str = "REVIEW_REQUIRED"
    related_record: Optional[str] = None
    created_at: str
    created_timestamp: Optional[str] = None

    def model_post_init(self, __context):
        if self.type is None:
            self.type = self.flag_type
        if self.similarity is None:
            self.similarity = self.similarity_score
        if self.confidence is None:
            self.confidence = self.similarity_score
        if self.created_timestamp is None:
            self.created_timestamp = self.created_at


class AnomalyListResponse(BaseModel):
    """Envelope wrapping the anomaly list for a single claim."""
    model_config = ConfigDict(from_attributes=True)

    claim_id: str
    total_anomalies: int
    total_count: Optional[int] = None
    review_status_summary: str
    anomalies: List[AnomalyFlagResponse]

    def model_post_init(self, __context):
        if self.total_count is None:
            self.total_count = self.total_anomalies


