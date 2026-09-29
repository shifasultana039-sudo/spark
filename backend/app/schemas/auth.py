"""
Authentication schemas for ReliefChain AI.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_id: Optional[str] = Field(None, example="USR-006")
    username: Optional[str] = Field(None, example="USR-006")
    email: Optional[str] = Field(None, example="senthil.n@citizen.tn.gov.in")
    password: Optional[str] = Field(None, example="demo123")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Full Name")
    email: str = Field(..., min_length=4, description="Email address")
    role: Optional[str] = Field("CITIZEN", description="Role: CITIZEN, GOVERNMENT_OFFICER, FIELD_ASSESSOR, ADMIN")
    organization: Optional[str] = Field(None, description="Organization or Household Name")
    household_ref: Optional[str] = Field(None, description="Household Reference ID (e.g. HH-1001)")
    password: Optional[str] = Field(None, description="Password")


class UserProfile(BaseModel):
    id: int
    user_id: str
    name: str
    email: str
    role: str
    organization: Optional[str] = None
    household_ref: Optional[str] = None
    wallet_address: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
