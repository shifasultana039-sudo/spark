"""
Authentication and Current User endpoints for ReliefChain AI (Step 17).
Provides:
- POST /auth/login (and /login): Authenticate user by user_id/username/email
- GET /auth/me (and /users/me, /me): Retrieve current authenticated user profile
"""

import re
from typing import Dict, Any
from fastapi import APIRouter, Depends

from ....core.database import get_db
from ....core.auth import get_current_user
from ....core.errors import UnauthorizedError, ValidationError
from ....schemas.auth import LoginRequest, LoginResponse, UserProfile, RegisterRequest

router = APIRouter(tags=["Authentication"])


@router.post(
    "/auth/register",
    response_model=LoginResponse,
    summary="Register a new account"
)
@router.post(
    "/register",
    response_model=LoginResponse,
    include_in_schema=False
)
def register_user(payload: RegisterRequest) -> LoginResponse:
    """
    Registers a new user account (Citizen, Government Officer, Field Assessor).
    Immediately returns session access token and user profile.
    """
    name = payload.name.strip()
    email = payload.email.strip()
    role = (payload.role or "CITIZEN").upper().strip()
    organization = payload.organization or ("Katpadi Resident" if role == "CITIZEN" else "Disaster Operations")
    household_ref = payload.household_ref or ("HH-1001" if role == "CITIZEN" else None)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?);", (email,))
        existing = cursor.fetchone()
        if existing:
            u = dict(existing)
            profile = UserProfile(
                id=u["id"],
                user_id=u["user_id"],
                name=u["name"],
                email=u["email"],
                role=u["role"],
                organization=u.get("organization"),
                household_ref=household_ref or u.get("household_ref"),
                wallet_address=u.get("wallet_address")
            )
            return LoginResponse(
                access_token=u["user_id"],
                token_type="bearer",
                user=profile
            )

        import secrets
        from datetime import datetime, timezone
        new_uid = f"USR-{secrets.token_hex(3).upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """INSERT INTO users (user_id, name, email, role, organization, created_at)
               VALUES (?, ?, ?, ?, ?, ?);""",
            (new_uid, name, email, role, organization, now_iso)
        )
        conn.commit()

        cursor.execute("SELECT * FROM users WHERE user_id = ?;", (new_uid,))
        new_user = dict(cursor.fetchone())

        profile = UserProfile(
            id=new_user["id"],
            user_id=new_user["user_id"],
            name=new_user["name"],
            email=new_user["email"],
            role=new_user["role"],
            organization=organization,
            household_ref=household_ref,
            wallet_address=None
        )

        return LoginResponse(
            access_token=new_uid,
            token_type="bearer",
            user=profile
        )


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login user and obtain access token"
)
@router.post(
    "/login",
    response_model=LoginResponse,
    include_in_schema=False
)
def login(payload: LoginRequest) -> LoginResponse:
    """
    Authenticates user by user_id, username, or email.
    Returns access token and verified user profile.
    """
    identifier = payload.user_id or payload.username or payload.email
    if not identifier or not identifier.strip():
        raise ValidationError("user_id, username, or email is required for login.")

    token = identifier.strip()

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Exact match on user_id, id, or email (case-insensitive)
        cursor.execute(
            "SELECT * FROM users WHERE user_id = ? OR id = ? OR LOWER(email) = LOWER(?) OR LOWER(user_id) = LOWER(?);",
            (token, token, token, token)
        )
        row = cursor.fetchone()

        # 2. Friendly role alias matching
        if not row:
            token_lower = token.lower().strip()
            alias_map = {
                "citizen": "USR-006",
                "officer": "USR-007",
                "gov": "USR-007",
                "government": "USR-007",
                "government_officer": "USR-007",
                "ngo": "USR-003",
                "assessor": "USR-003",
                "field_assessor": "USR-003",
                "volunteer": "USR-003",
                "admin": "USR-001",
                "senthil": "USR-006",
                "senthil nathan": "USR-006",
                "rajesh": "USR-007",
                "rajesh v": "USR-007",
                "kavitha": "USR-003",
                "kavitha sundaram": "USR-003",
                "ananya": "USR-001"
            }
            if token_lower in alias_map:
                cursor.execute("SELECT * FROM users WHERE user_id = ?;", (alias_map[token_lower],))
                row = cursor.fetchone()

        # 3. Partial match on name
        if not row:
            cursor.execute(
                "SELECT * FROM users WHERE LOWER(name) LIKE ? ORDER BY id ASC LIMIT 1;",
                (f"%{token.lower()}%",)
            )
            row = cursor.fetchone()

        # 4. If new user identifier, automatically register citizen account
        if not row:
            import secrets
            from datetime import datetime, timezone
            new_uid = f"USR-{secrets.token_hex(3).upper()}"
            name_clean = token.split("@")[0].replace(".", " ").replace("-", " ").title()
            email_clean = token if "@" in token else f"{token.lower()}@reliefchain.org"
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """INSERT INTO users (user_id, name, email, role, organization, created_at)
                   VALUES (?, ?, ?, 'CITIZEN', 'Registered Citizen (HH-1001)', ?);""",
                (new_uid, name_clean, email_clean, now_iso)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?;", (new_uid,))
            row = cursor.fetchone()

        if not row:
            raise UnauthorizedError(f"Unable to authenticate identifier '{token}'.")

        user = dict(row)
        user_household = None
        org = user.get("organization") or ""
        if "HH-" in org:
            match = re.search(r"HH-\d+", org)
            if match:
                user_household = match.group(0)

        if not user_household:
            cursor.execute(
                "SELECT household_ref FROM households WHERE head_of_household = ? LIMIT 1;",
                (user.get("name"),)
            )
            hh_row = cursor.fetchone()
            if hh_row:
                user_household = hh_row["household_ref"]

        user["household_ref"] = user_household

        profile = UserProfile(
            id=user["id"],
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            organization=user.get("organization"),
            household_ref=user.get("household_ref"),
            wallet_address=user.get("wallet_address")
        )

        return LoginResponse(
            access_token=user["user_id"],
            token_type="bearer",
            user=profile
        )


@router.get(
    "/auth/me",
    response_model=UserProfile,
    summary="Get current authenticated user profile"
)
@router.get(
    "/users/me",
    response_model=UserProfile,
    summary="Get current user (alias)"
)
@router.get(
    "/me",
    response_model=UserProfile,
    include_in_schema=False
)
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfile:
    """
    Returns profile information for the currently authenticated user.
    """
    return UserProfile(
        id=current_user["id"],
        user_id=current_user["user_id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        organization=current_user.get("organization"),
        household_ref=current_user.get("household_ref"),
        wallet_address=current_user.get("wallet_address")
    )
