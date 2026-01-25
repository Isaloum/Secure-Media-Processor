"""
File Processing Lambda Function
Handles file upload, download, and management with S3
"""
import json
import os
import sys
import hashlib
import uuid
from datetime import datetime, timedelta

# Add shared layer to path
sys.path.insert(0, "/opt/python")

import boto3
from db_utils import execute_query
from response import (
    success_response,
    error_response,
    validation_error,
    not_found_error,
)

s3_client = boto3.client("s3")
MEDIA_BUCKET = os.environ["MEDIA_BUCKET"]


def lambda_handler(event, context):
    """Main Lambda handler for file endpoints"""
    try:
        # Parse request
        method = event.get("httpMethod")
        path = event.get("path", "")
        body = json.loads(event.get("body", "{}"))
        path_params = event.get("pathParameters", {})

        # Get user from JWT (implement JWT validation in production)
        user_id = extract_user_id(event)
        if not user_id:
            return error_response("Unauthorized", 401)

        # Route to appropriate handler
        if method == "POST" and "/files" in path and not path_params:
            return handle_upload_request(body, user_id)
        elif method == "GET" and path_params and path_params.get("id"):
            return handle_download(path_params["id"], user_id)
        elif method == "DELETE" and path_params and path_params.get("id"):
            return handle_delete(path_params["id"], user_id)
        elif method == "GET" and "/files" in path:
            return handle_list_files(user_id)
        else:
            return error_response("Unknown endpoint", 404)

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response("Internal server error", 500)


def extract_user_id(event):
    """Extract user ID from JWT token (simplified - implement proper JWT validation)"""
    # In production, validate JWT token from Authorization header
    # For now, return a mock user ID
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization", "")

    # TODO: Implement proper JWT validation
    # For demo purposes, extract from mock token
    return "mock-user-id-123"


def handle_upload_request(body, user_id):
    """Generate presigned URL for S3 upload"""
    # Validate input
    filename = body.get("filename")
    file_size = body.get("file_size")
    mime_type = body.get("mime_type", "application/octet-stream")

    if not filename or not file_size:
        return validation_error("Filename and file_size are required")

    # Generate unique file ID
    file_id = str(uuid.uuid4())
    s3_key = f"uploads/{user_id}/{file_id}/{filename}"

    # Generate presigned POST URL
    presigned_post = s3_client.generate_presigned_post(
        Bucket=MEDIA_BUCKET,
        Key=s3_key,
        Fields={"Content-Type": mime_type},
        Conditions=[
            {"Content-Type": mime_type},
            ["content-length-range", 1, 5 * 1024 * 1024 * 1024]  # Max 5GB
        ],
        ExpiresIn=900  # 15 minutes
    )

    # Store file metadata in database
    execute_query(
        """
        INSERT INTO files (id, user_id, s3_key, original_filename, file_size, mime_type, upload_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (file_id, user_id, s3_key, filename, file_size, mime_type, datetime.utcnow()),
        fetch=False
    )

    return success_response({
        "file_id": file_id,
        "upload_url": presigned_post["url"],
        "upload_fields": presigned_post["fields"],
        "expires_in": 900
    })


def handle_download(file_id, user_id):
    """Generate presigned URL for S3 download"""
    # Fetch file metadata
    files = execute_query(
        "SELECT s3_key, original_filename FROM files WHERE id = %s AND user_id = %s",
        (file_id, user_id)
    )

    if not files:
        return not_found_error("File not found")

    file_data = files[0]

    # Generate presigned URL for download
    download_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": MEDIA_BUCKET,
            "Key": file_data["s3_key"]
        },
        ExpiresIn=3600  # 1 hour
    )

    return success_response({
        "file_id": file_id,
        "filename": file_data["original_filename"],
        "download_url": download_url,
        "expires_in": 3600
    })


def handle_delete(file_id, user_id):
    """Delete file from S3 and database"""
    # Fetch file metadata
    files = execute_query(
        "SELECT s3_key FROM files WHERE id = %s AND user_id = %s",
        (file_id, user_id)
    )

    if not files:
        return not_found_error("File not found")

    file_data = files[0]

    # Delete from S3
    s3_client.delete_object(
        Bucket=MEDIA_BUCKET,
        Key=file_data["s3_key"]
    )

    # Delete from database
    execute_query(
        "DELETE FROM files WHERE id = %s AND user_id = %s",
        (file_id, user_id),
        fetch=False
    )

    return success_response({
        "message": "File deleted successfully",
        "file_id": file_id
    })


def handle_list_files(user_id):
    """List all files for a user"""
    files = execute_query(
        """
        SELECT id, original_filename, file_size, mime_type, upload_timestamp, malware_scan_status
        FROM files
        WHERE user_id = %s
        ORDER BY upload_timestamp DESC
        LIMIT 100
        """,
        (user_id,)
    )

    return success_response({
        "files": files,
        "count": len(files)
    })
