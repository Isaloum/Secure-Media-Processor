"""
Authentication Lambda Function
Handles user registration and login with JWT tokens
"""
import json
import os
import sys
from datetime import datetime, timedelta

# Add shared layer to path
sys.path.insert(0, "/opt/python")

import boto3
import bcrypt
import jwt
from db_utils import execute_query
from response import (
    success_response,
    error_response,
    validation_error,
    unauthorized_error,
)


def get_jwt_secret():
    """Retrieve JWT secret from Secrets Manager"""
    secret_name = os.environ["JWT_SECRET_NAME"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])["jwt_secret"]


def lambda_handler(event, context):
    """Main Lambda handler for auth endpoints"""
    try:
        # Parse request
        path = event.get("path", "")
        body = json.loads(event.get("body", "{}"))

        # Route to appropriate handler
        if "/register" in path:
            return handle_register(body)
        elif "/login" in path:
            return handle_login(body)
        else:
            return error_response("Unknown endpoint", 404)

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response("Internal server error", 500)


def handle_register(body):
    """Handle user registration"""
    # Validate input
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return validation_error("Email and password are required")

    if len(password) < 8:
        return validation_error("Password must be at least 8 characters")

    # Check if user already exists
    existing_user = execute_query(
        "SELECT id FROM users WHERE email = %s",
        (email,)
    )

    if existing_user:
        return error_response("User already exists", 409)

    # Hash password
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Create user
    execute_query(
        """
        INSERT INTO users (email, password_hash, created_at, subscription_tier)
        VALUES (%s, %s, %s, %s)
        """,
        (email, password_hash, datetime.utcnow(), "free"),
        fetch=False
    )

    return success_response({
        "message": "User registered successfully",
        "email": email
    }, 201)


def handle_login(body):
    """Handle user login and JWT generation"""
    # Validate input
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return validation_error("Email and password are required")

    # Fetch user
    users = execute_query(
        "SELECT id, email, password_hash FROM users WHERE email = %s",
        (email,)
    )

    if not users:
        return unauthorized_error("Invalid credentials")

    user = users[0]

    # Verify password
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return unauthorized_error("Invalid credentials")

    # Update last login
    execute_query(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (datetime.utcnow(), user["id"]),
        fetch=False
    )

    # Generate JWT token
    jwt_secret = get_jwt_secret()
    token = jwt.encode(
        {
            "user_id": str(user["id"]),
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        jwt_secret,
        algorithm="HS256"
    )

    return success_response({
        "token": token,
        "user": {
            "id": str(user["id"]),
            "email": user["email"]
        }
    })
