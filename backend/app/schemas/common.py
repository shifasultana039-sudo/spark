"""
Common schemas used across multiple domain modules.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field(..., example="HEALTHY")
    database: str = Field(..., example="CONNECTED")
    storage: str = Field(..., example="ACCESSIBLE")
    version: str = Field("1.0.0", example="1.0.0")
    timestamp: str

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
