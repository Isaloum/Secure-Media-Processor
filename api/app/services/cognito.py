"""Cognito service for authentication"""

from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class CognitoService:
    """Service for Cognito operations"""

    def __init__(self):
        self.client = boto3.client(
            "cognito-idp",
            region_name=settings.aws_region,
        )
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id

    def sign_up(self, email: str, password: str, name: Optional[str] = None) -> dict:
        """Sign up a new user"""
        user_attributes = [{"Name": "email", "Value": email}]

        if name:
            user_attributes.append({"Name": "name", "Value": name})

        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=user_attributes,
            )
            return {
                "success": True,
                "user_sub": response.get("UserSub"),
                "confirmed": response.get("UserConfirmed", False),
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def confirm_sign_up(self, email: str, confirmation_code: str) -> dict:
        """Confirm user sign up with verification code"""
        try:
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=confirmation_code,
            )
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def resend_confirmation_code(self, email: str) -> dict:
        """Resend confirmation code"""
        try:
            self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=email,
            )
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def sign_in(self, email: str, password: str) -> dict:
        """Sign in a user"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password,
                },
            )

            auth_result = response.get("AuthenticationResult", {})
            return {
                "success": True,
                "access_token": auth_result.get("AccessToken"),
                "id_token": auth_result.get("IdToken"),
                "refresh_token": auth_result.get("RefreshToken"),
                "expires_in": auth_result.get("ExpiresIn", 3600),
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                },
            )

            auth_result = response.get("AuthenticationResult", {})
            return {
                "success": True,
                "access_token": auth_result.get("AccessToken"),
                "id_token": auth_result.get("IdToken"),
                "expires_in": auth_result.get("ExpiresIn", 3600),
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def forgot_password(self, email: str) -> dict:
        """Initiate forgot password flow"""
        try:
            self.client.forgot_password(
                ClientId=self.client_id,
                Username=email,
            )
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def confirm_forgot_password(
        self, email: str, confirmation_code: str, new_password: str
    ) -> dict:
        """Confirm forgot password with new password"""
        try:
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=confirmation_code,
                Password=new_password,
            )
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def get_user(self, access_token: str) -> dict:
        """Get user info from access token"""
        try:
            response = self.client.get_user(AccessToken=access_token)

            # Parse user attributes
            attributes = {}
            for attr in response.get("UserAttributes", []):
                attributes[attr["Name"]] = attr["Value"]

            return {
                "success": True,
                "username": response.get("Username"),
                "user_id": attributes.get("sub"),
                "email": attributes.get("email"),
                "email_verified": attributes.get("email_verified") == "true",
                "name": attributes.get("name"),
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def sign_out(self, access_token: str) -> dict:
        """Sign out user (global sign out)"""
        try:
            self.client.global_sign_out(AccessToken=access_token)
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}

    def admin_get_user(self, email: str) -> dict:
        """Admin: Get user by email"""
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email,
            )

            attributes = {}
            for attr in response.get("UserAttributes", []):
                attributes[attr["Name"]] = attr["Value"]

            return {
                "success": True,
                "user_id": attributes.get("sub"),
                "email": attributes.get("email"),
                "status": response.get("UserStatus"),
                "enabled": response.get("Enabled"),
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            return {"success": False, "error": error_code}

    def admin_update_user_attributes(self, email: str, attributes: dict) -> dict:
        """Admin: Update user attributes"""
        user_attributes = [
            {"Name": key, "Value": value} for key, value in attributes.items()
        ]

        try:
            self.client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
            )
            return {"success": True}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return {"success": False, "error": error_code, "message": error_message}


# Singleton instance
cognito_service = CognitoService()
