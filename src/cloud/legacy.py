"""Cloud storage module for secure media backup and synchronization."""

import os
import hashlib
from pathlib import Path
from typing import Union, Optional, Dict, List
from datetime import datetime
import json
import boto3
from botocore.exceptions import ClientError
import logging


logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manage cloud storage operations for encrypted media files."""
    
    def __init__(self, 
                 bucket_name: str,
                 region: str = 'us-east-1',
                 access_key: Optional[str] = None,
                 secret_key: Optional[str] = None):
        """Initialize cloud storage manager.
        
        Args:
            bucket_name: Name of the S3 bucket.
            region: AWS region for the bucket.
            access_key: AWS access key (uses environment variable if not provided).
            secret_key: AWS secret key (uses environment variable if not provided).
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Initialize S3 client
        session_kwargs = {'region_name': region}
        if access_key and secret_key:
            session_kwargs['aws_access_key_id'] = access_key
            session_kwargs['aws_secret_access_key'] = secret_key
        
        self.s3_client = boto3.client('s3', **session_kwargs)
        self.s3_resource = boto3.resource('s3', **session_kwargs)
        
    def _calculate_checksum(self, file_path: Union[str, Path]) -> str:
        """Calculate SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            Hexadecimal checksum string.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def upload_file(self, 
                    file_path: Union[str, Path],
                    remote_key: Optional[str] = None,
                    metadata: Optional[Dict[str, str]] = None,
                    encryption: str = 'AES256') -> Dict[str, any]:
        """Upload a file to cloud storage.
        
        Args:
            file_path: Path to the local file.
            remote_key: S3 object key (uses filename if not provided).
            metadata: Additional metadata to attach to the file.
            encryption: Server-side encryption method ('AES256' or 'aws:kms').
            
        Returns:
            Dictionary containing upload information.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use filename as key if not provided
        if remote_key is None:
            remote_key = file_path.name
        
        # Calculate checksum
        checksum = self._calculate_checksum(file_path)
        
        # Prepare metadata
        file_metadata = metadata or {}
        file_metadata['checksum'] = checksum
        file_metadata['upload_time'] = datetime.utcnow().isoformat()
        file_metadata['original_name'] = file_path.name
        
        try:
            # Upload with server-side encryption
            extra_args = {
                'Metadata': file_metadata,
                'ServerSideEncryption': encryption
            }
            
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                remote_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Successfully uploaded {file_path} to {remote_key}")
            
            return {
                'success': True,
                'remote_key': remote_key,
                'checksum': checksum,
                'size': file_path.stat().st_size,
                'timestamp': file_metadata['upload_time']
            }
            
        except ClientError as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(self,
                      remote_key: str,
                      local_path: Union[str, Path],
                      verify_checksum: bool = True) -> Dict[str, any]:
        """Download a file from cloud storage.
        
        Args:
            remote_key: S3 object key.
            local_path: Path where the file will be saved.
            verify_checksum: Whether to verify file integrity after download.
            
        Returns:
            Dictionary containing download information.
        """
        local_path = Path(local_path)
        
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=remote_key
            )
            
            stored_checksum = response.get('Metadata', {}).get('checksum')
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                remote_key,
                str(local_path)
            )
            
            # Verify checksum if requested
            if verify_checksum and stored_checksum:
                local_checksum = self._calculate_checksum(local_path)
                if local_checksum != stored_checksum:
                    local_path.unlink()  # Delete corrupted file
                    raise ValueError("Checksum verification failed")
            
            logger.info(f"Successfully downloaded {remote_key} to {local_path}")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'size': local_path.stat().st_size,
                'checksum_verified': verify_checksum
            }
            
        except ClientError as e:
            logger.error(f"Download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, remote_key: str) -> Dict[str, any]:
        """Delete a file from cloud storage.
        
        Args:
            remote_key: S3 object key.
            
        Returns:
            Dictionary containing deletion information.
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=remote_key
            )
            
            logger.info(f"Successfully deleted {remote_key}")
            
            return {
                'success': True,
                'remote_key': remote_key
            }
            
        except ClientError as e:
            logger.error(f"Deletion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_files(self, prefix: str = '') -> List[Dict[str, any]]:
        """List files in cloud storage.
        
        Args:
            prefix: Filter results by key prefix.
            
        Returns:
            List of file information dictionaries.
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag']
                })
            
            return files
            
        except ClientError as e:
            logger.error(f"List operation failed: {e}")
            return []
    
    def sync_directory(self,
                       local_dir: Union[str, Path],
                       remote_prefix: str = '',
                       encryption: str = 'AES256') -> Dict[str, any]:
        """Sync a local directory to cloud storage.
        
        Args:
            local_dir: Path to the local directory.
            remote_prefix: Prefix for remote keys.
            encryption: Server-side encryption method.
            
        Returns:
            Dictionary containing sync statistics.
        """
        local_dir = Path(local_dir)
        
        if not local_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {local_dir}")
        
        uploaded = []
        failed = []
        
        # Upload all files in directory
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Calculate relative path for remote key
                relative_path = file_path.relative_to(local_dir)
                remote_key = f"{remote_prefix}/{relative_path}".strip('/')
                
                result = self.upload_file(
                    file_path,
                    remote_key=remote_key,
                    encryption=encryption
                )
                
                if result['success']:
                    uploaded.append(remote_key)
                else:
                    failed.append({'file': str(file_path), 'error': result.get('error')})
        
        return {
            'uploaded_count': len(uploaded),
            'failed_count': len(failed),
            'uploaded_files': uploaded,
            'failed_files': failed
        }
    
    def get_file_metadata(self, remote_key: str) -> Dict[str, any]:
        """Get metadata for a file in cloud storage.
        
        Args:
            remote_key: S3 object key.
            
        Returns:
            Dictionary containing file metadata.
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=remote_key
            )
            
            return {
                'success': True,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'metadata': response.get('Metadata', {}),
                'encryption': response.get('ServerSideEncryption')
            }
            
        except ClientError as e:
            logger.error(f"Failed to get metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }