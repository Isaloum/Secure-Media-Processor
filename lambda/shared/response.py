"""
Standard API response helpers for Lambda functions
"""
import json
from typing import Any, Dict


def success_response(data: Any, status_code: int = 200) -> Dict:
    """Return a successful API response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps({"success": True, "data": data}),
    }


def error_response(message: str, status_code: int = 400) -> Dict:
    """Return an error API response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps({"success": False, "error": message}),
    }


def validation_error(message: str) -> Dict:
    """Return a validation error response (400)"""
    return error_response(message, 400)


def unauthorized_error(message: str = "Unauthorized") -> Dict:
    """Return an unauthorized error response (401)"""
    return error_response(message, 401)


def forbidden_error(message: str = "Forbidden") -> Dict:
    """Return a forbidden error response (403)"""
    return error_response(message, 403)


def not_found_error(message: str = "Not found") -> Dict:
    """Return a not found error response (404)"""
    return error_response(message, 404)


def internal_error(message: str = "Internal server error") -> Dict:
    """Return an internal server error response (500)"""
    return error_response(message, 500)
