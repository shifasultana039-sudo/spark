"""
Standardized response structures and helper utilities.
"""

from typing import Any, Dict, Optional

def success_response(data: Any, message: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Wraps successful data in a standard API envelope."""
    payload: Dict[str, Any] = {
        "success": True,
        "data": data
    }
    if message:
        payload["message"] = message
    if meta:
        payload["meta"] = meta
    return payload

def error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Creates a standardized error response dictionary."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
