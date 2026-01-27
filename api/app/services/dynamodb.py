"""DynamoDB service for database operations"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class DynamoDBService:
    """Service for DynamoDB operations"""

    def __init__(self):
        self.client = boto3.client("dynamodb", region_name=settings.aws_region)
        self.resource = boto3.resource("dynamodb", region_name=settings.aws_region)

    def _get_table(self, table_name: str):
        """Get DynamoDB table resource"""
        return self.resource.Table(table_name)

    @staticmethod
    def _now() -> str:
        """Get current ISO timestamp"""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # User Operations
    # -------------------------------------------------------------------------
    def create_user(self, user_id: str, email: str, name: Optional[str] = None) -> Dict:
        """Create a new user"""
        table = self._get_table(settings.dynamodb_users_table)
        now = self._now()

        item = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "license_tier": "free",
            "storage_used_bytes": 0,
            "created_at": now,
            "updated_at": now,
        }

        table.put_item(Item=item)
        return item

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        table = self._get_table(settings.dynamodb_users_table)

        try:
            response = table.get_item(Key={"user_id": user_id})
            return response.get("Item")
        except ClientError:
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        table = self._get_table(settings.dynamodb_users_table)

        try:
            response = table.query(
                IndexName="email-index",
                KeyConditionExpression="email = :email",
                ExpressionAttributeValues={":email": email},
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError:
            return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Update user attributes"""
        table = self._get_table(settings.dynamodb_users_table)

        update_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}

        for key, value in updates.items():
            safe_key = f"#{key}"
            value_key = f":{key}"
            update_expr_parts.append(f"{safe_key} = {value_key}")
            expr_attr_values[value_key] = value
            expr_attr_names[safe_key] = key

        # Always update updated_at
        update_expr_parts.append("#updated_at = :updated_at")
        expr_attr_values[":updated_at"] = self._now()
        expr_attr_names["#updated_at"] = "updated_at"

        try:
            response = table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET " + ", ".join(update_expr_parts),
                ExpressionAttributeValues=expr_attr_values,
                ExpressionAttributeNames=expr_attr_names,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError:
            return None

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------
    def create_file(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        s3_key: str,
        encrypted: bool = True,
    ) -> Dict:
        """Create a new file record"""
        table = self._get_table(settings.dynamodb_files_table)
        file_id = self._generate_id()
        now = self._now()

        item = {
            "file_id": file_id,
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "s3_key": s3_key,
            "encrypted": encrypted,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        table.put_item(Item=item)
        return item

    def get_file(self, file_id: str, user_id: str) -> Optional[Dict]:
        """Get file by ID and user ID"""
        table = self._get_table(settings.dynamodb_files_table)

        try:
            response = table.get_item(Key={"file_id": file_id, "user_id": user_id})
            return response.get("Item")
        except ClientError:
            return None

    def list_user_files(
        self, user_id: str, limit: int = 20, last_key: Optional[str] = None
    ) -> Dict:
        """List files for a user"""
        table = self._get_table(settings.dynamodb_files_table)

        query_params = {
            "IndexName": "user-files-index",
            "KeyConditionExpression": "user_id = :user_id",
            "ExpressionAttributeValues": {":user_id": user_id},
            "ScanIndexForward": False,  # Newest first
            "Limit": limit,
        }

        if last_key:
            query_params["ExclusiveStartKey"] = {"user_id": user_id, "created_at": last_key}

        try:
            response = table.query(**query_params)
            return {
                "items": response.get("Items", []),
                "last_key": response.get("LastEvaluatedKey", {}).get("created_at"),
            }
        except ClientError:
            return {"items": [], "last_key": None}

    def update_file_status(self, file_id: str, user_id: str, status: str) -> Optional[Dict]:
        """Update file status"""
        table = self._get_table(settings.dynamodb_files_table)

        try:
            response = table.update_item(
                Key={"file_id": file_id, "user_id": user_id},
                UpdateExpression="SET #status = :status, #updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status", "#updated_at": "updated_at"},
                ExpressionAttributeValues={":status": status, ":updated_at": self._now()},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError:
            return None

    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file record"""
        table = self._get_table(settings.dynamodb_files_table)

        try:
            table.delete_item(Key={"file_id": file_id, "user_id": user_id})
            return True
        except ClientError:
            return False

    # -------------------------------------------------------------------------
    # License Operations
    # -------------------------------------------------------------------------
    def create_license(
        self,
        license_key: str,
        tier: str,
        gumroad_sale_id: Optional[str] = None,
        max_activations: int = 3,
    ) -> Dict:
        """Create a new license"""
        table = self._get_table(settings.dynamodb_licenses_table)
        now = self._now()

        item = {
            "license_key": license_key,
            "tier": tier,
            "status": "active",
            "activations": 0,
            "max_activations": max_activations,
            "gumroad_sale_id": gumroad_sale_id,
            "created_at": now,
        }

        table.put_item(Item=item)
        return item

    def get_license(self, license_key: str) -> Optional[Dict]:
        """Get license by key"""
        table = self._get_table(settings.dynamodb_licenses_table)

        try:
            response = table.get_item(Key={"license_key": license_key})
            return response.get("Item")
        except ClientError:
            return None

    def activate_license(self, license_key: str, user_id: str) -> Optional[Dict]:
        """Activate a license for a user"""
        table = self._get_table(settings.dynamodb_licenses_table)

        try:
            response = table.update_item(
                Key={"license_key": license_key},
                UpdateExpression="SET user_id = :user_id, activations = activations + :one",
                ConditionExpression="activations < max_activations AND #status = :active",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":user_id": user_id,
                    ":one": 1,
                    ":active": "active",
                },
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError:
            return None

    # -------------------------------------------------------------------------
    # Usage Operations
    # -------------------------------------------------------------------------
    def increment_usage(self, user_id: str, period: str, field: str, amount: int = 1) -> Dict:
        """Increment usage counter"""
        table = self._get_table(settings.dynamodb_usage_table)

        try:
            response = table.update_item(
                Key={"user_id": user_id, "period": period},
                UpdateExpression=f"SET #{field} = if_not_exists(#{field}, :zero) + :amount",
                ExpressionAttributeNames={f"#{field}": field},
                ExpressionAttributeValues={":zero": 0, ":amount": amount},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})
        except ClientError:
            return {}

    def get_usage(self, user_id: str, period: str) -> Optional[Dict]:
        """Get usage for a period"""
        table = self._get_table(settings.dynamodb_usage_table)

        try:
            response = table.get_item(Key={"user_id": user_id, "period": period})
            return response.get("Item")
        except ClientError:
            return None


# Singleton instance
db_service = DynamoDBService()
