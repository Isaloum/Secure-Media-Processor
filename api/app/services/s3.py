"""S3 service for file storage operations"""

import uuid
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class S3Service:
    """Service for S3 operations"""

    def __init__(self):
        self.client = boto3.client("s3", region_name=settings.aws_region)
        self.bucket = settings.s3_media_bucket

    def generate_upload_key(self, user_id: str, filename: str) -> str:
        """Generate a unique S3 key for upload"""
        file_id = str(uuid.uuid4())
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        return f"users/{user_id}/files/{file_id}/{safe_filename}"

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> Dict:
        """Generate a presigned URL for file upload"""
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
                ExpiresIn=expires_in,
            )
            return {"url": url, "key": key, "expires_in": expires_in}
        except ClientError as e:
            raise Exception(f"Failed to generate upload URL: {e}")

    def generate_presigned_download_url(
        self,
        key: str,
        filename: Optional[str] = None,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for file download"""
        params = {
            "Bucket": self.bucket,
            "Key": key,
        }

        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate download URL: {e}")

    def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_file_metadata(self, key: str) -> Optional[Dict]:
        """Get file metadata from S3"""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return {
                "content_type": response.get("ContentType"),
                "size_bytes": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError:
            return None

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def list_user_files(self, user_id: str, prefix: str = "") -> list:
        """List all files for a user"""
        full_prefix = f"users/{user_id}/files/{prefix}"

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=full_prefix,
            )
            return response.get("Contents", [])
        except ClientError:
            return []

    def get_user_storage_used(self, user_id: str) -> int:
        """Calculate total storage used by a user"""
        files = self.list_user_files(user_id)
        return sum(f.get("Size", 0) for f in files)

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy a file within the bucket"""
        try:
            self.client.copy_object(
                Bucket=self.bucket,
                Key=dest_key,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                ServerSideEncryption="AES256",
            )
            return True
        except ClientError:
            return False


# Singleton instance
s3_service = S3Service()
