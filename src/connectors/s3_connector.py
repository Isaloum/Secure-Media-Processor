"""AWS S3 connector implementation.

This module provides a connector for AWS S3 cloud storage that implements
the CloudConnector interface.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone
import logging

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base_connector import CloudConnector


logger = logging.getLogger(__name__)


class S3Connector(CloudConnector):
    """AWS S3 cloud storage connector.
    
    This connector provides integration with Amazon S3 for secure file storage.
    Supports server-side encryption, checksum verification, and metadata management.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region: str = 'us-east-1',
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        encryption: str = 'AES256'
    ):
        """Initialize S3 connector.
        
        Args:
            bucket_name: Name of the S3 bucket.
            region: AWS region for the bucket.
            access_key: AWS access key (uses environment variable if not provided).
            secret_key: AWS secret key (uses environment variable if not provided).
            encryption: Server-side encryption method ('AES256' or 'aws:kms').
        """
        super().__init__()
        self.bucket_name = bucket_name
        self.region = region
        self.encryption = encryption
        self.access_key = access_key
        self.secret_key = secret_key
        self.s3_client = None
        self.s3_resource = None
    
    def connect(self) -> bool:
        """Establish connection to AWS S3.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            session_kwargs = {'region_name': self.region}
            
            if self.access_key and self.secret_key:
                session_kwargs['aws_access_key_id'] = self.access_key
                session_kwargs['aws_secret_access_key'] = self.secret_key
            
            self.s3_client = boto3.client('s3', **session_kwargs)
            self.s3_resource = boto3.resource('s3', **session_kwargs)
            
            # Test connection by checking if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            self._connected = True
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
            return True
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to connect to S3: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from AWS S3.
        
        Returns:
            bool: True if disconnection successful.
        """
        self.s3_client = None
        self.s3_resource = None
        self._connected = False
        logger.info("Disconnected from S3")
        return True
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to S3.
        
        Args:
            file_path: Path to the local file.
            remote_path: S3 object key.
            metadata: Optional metadata to attach to the file.
            
        Returns:
            Dictionary containing upload result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to S3'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        file_path = Path(file_path)

        if not file_path.exists():
            return {'success': False, 'error': f'File not found: {file_path}'}

        try:
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Prepare metadata
            file_metadata = metadata or {}
            file_metadata['checksum'] = checksum
            file_metadata['upload_time'] = datetime.now(timezone.utc).isoformat()
            file_metadata['original_name'] = file_path.name
            
            # Upload with server-side encryption
            extra_args = {
                'Metadata': file_metadata,
                'ServerSideEncryption': self.encryption
            }
            
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                remote_path,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Successfully uploaded {file_path} to s3://{self.bucket_name}/{remote_path}")
            
            return {
                'success': True,
                'remote_path': remote_path,
                'checksum': checksum,
                'size': file_path.stat().st_size,
                'timestamp': file_metadata['upload_time']
            }
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Download a file from S3.
        
        Args:
            remote_path: S3 object key.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.
            
        Returns:
            Dictionary containing download result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to S3'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        local_path = Path(local_path)
        
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            
            stored_checksum = response.get('Metadata', {}).get('checksum')
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                remote_path,
                str(local_path)
            )
            
            # Verify checksum if requested
            checksum_verified = False
            if verify_checksum and stored_checksum:
                local_checksum = self._calculate_checksum(local_path)
                if local_checksum != stored_checksum:
                    local_path.unlink()  # Delete corrupted file
                    return {
                        'success': False,
                        'error': 'Checksum verification failed'
                    }
                checksum_verified = True
            
            logger.info(f"Successfully downloaded s3://{self.bucket_name}/{remote_path} to {local_path}")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'size': local_path.stat().st_size,
                'checksum_verified': checksum_verified
            }
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from S3.

        Args:
            remote_path: S3 object key.

        Returns:
            Dictionary containing deletion result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to S3'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            
            logger.info(f"Successfully deleted s3://{self.bucket_name}/{remote_path}")
            
            return {
                'success': True,
                'remote_path': remote_path
            }
            
        except ClientError as e:
            logger.error(f"S3 deletion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files in S3 bucket.
        
        Args:
            prefix: Filter results by key prefix.
            
        Returns:
            List of file information dictionaries.
        """
        if not self._connected:
            logger.error("Not connected to S3")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'path': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'checksum': obj.get('ETag', '').strip('"')
                })
            
            return files
            
        except ClientError as e:
            logger.error(f"S3 list operation failed: {e}")
            return []
    
    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a file in S3.

        Args:
            remote_path: S3 object key.

        Returns:
            Dictionary containing file metadata.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to S3'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            
            return {
                'success': True,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'metadata': response.get('Metadata', {}),
                'checksum': response.get('ETag', '').strip('"'),
                'encryption': response.get('ServerSideEncryption')
            }
            
        except ClientError as e:
            logger.error(f"Failed to get S3 metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }
