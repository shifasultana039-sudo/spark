"""
Authentication and Authorization dependencies for ReliefChain AI.
Supports Bearer tokens (user_id/email/JWT), X-User-Id headers, and query parameters.
Enforces role-based access control and citizen data isolation.
"""

from typing import Optional, Dict, Any, List
from fastapi import Request, Depends, status
from .database import get_db
from .errors import UnauthorizedError, ForbiddenError

def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Resolves authenticated user from incoming request.
    Checks:
    1. Authorization header: 'Bearer <user_id_or_token>' or '<user_id>'
    2. X-User-Id header
    3. Query parameter: ?user_id=...
    """
    token: Optional[str] = None
    
    # 1. Authorization header
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        else:
            token = auth_header.strip()

    # 2. X-User-Id header
    if not token:
        token = request.headers.get("X-User-Id") or request.headers.get("x-user-id")

    # 3. Query param fallback (convenient for testing and downloads)
    if not token:
        token = request.query_params.get("user_id")

    if not token:
        raise UnauthorizedError("Authentication required. Please provide credentials via Authorization header (Bearer <user_id>) or X-User-Id.")

    # Lookup user in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ? OR id = ? OR email = ?;", (token, token, token))
        user = cursor.fetchone()

        if not user:
            raise UnauthorizedError(f"User not found for identifier '{token}'.")

        # Attach household_ref if known from organization (e.g. 'Katpadi Resident (HH-1001)') or households table
        user = dict(user)
        user_household = None
        org = user.get("organization") or ""
        if "HH-" in org:
            import re
            match = re.search(r"HH-\d+", org)
            if match:
                user_household = match.group(0)

        if not user_household:
            cursor.execute("SELECT household_ref FROM households WHERE head_of_household = ? LIMIT 1;", (user.get("name"),))
            hh_row = cursor.fetchone()
            if hh_row:
                user_household = hh_row["household_ref"]

        user["household_ref"] = user_household
        return user


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Resolves authenticated user if credentials provided, else returns None."""
    try:
        return get_current_user(request)
    except Exception:
        return None


def is_officer_or_admin(user: Dict[str, Any]) -> bool:
    """Returns True if user has government officer or administrator clearance."""
    role = (user.get("role") or "").upper()
    return role in {"ADMIN", "GOVERNMENT_OFFICER", "RELIEF_COORDINATOR"}


def is_citizen(user: Dict[str, Any]) -> bool:
    """Returns True if user is a citizen."""
    return (user.get("role") or "").upper() == "CITIZEN"


def require_role(allowed_roles: List[str]):
    """FastAPI dependency to enforce specific user roles."""
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        role = (user.get("role") or "").upper()
        if role not in [r.upper() for r in allowed_roles]:
            raise ForbiddenError(f"Role '{role}' is not authorized. Required: {allowed_roles}")
        return user
    return role_checker
