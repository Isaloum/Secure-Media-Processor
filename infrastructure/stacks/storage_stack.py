"""
Storage Stack - S3 Buckets for media files and static content
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class StorageStack(Stack):
    """S3 storage infrastructure"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Media Files Bucket (encrypted user uploads)
        self.media_bucket = s3.Bucket(
            self,
            "MediaBucket",
            bucket_name=None,  # Auto-generate unique name
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            enforce_ssl=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                    ],
                    allowed_origins=["*"],  # Configure with your domain
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
            lifecycle_rules=[
                # Delete incomplete multipart uploads after 7 days
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUpload",
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                    enabled=True,
                ),
                # Delete old versions after 90 days
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(90),
                    enabled=True,
                ),
                # Transition to Glacier for long-term storage (optional)
                s3.LifecycleRule(
                    id="TransitionToGlacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(365),
                        )
                    ],
                    enabled=False,  # Enable if needed
                ),
            ],
        )

        # Access Logs Bucket
        self.logs_bucket = s3.Bucket(
            self,
            "LogsBucket",
            bucket_name=None,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldLogs",
                    expiration=Duration.days(30),
                    enabled=True,
                )
            ],
        )

        # Enable server access logging for media bucket
        self.media_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountPrincipal(Stack.of(self).account)],
                actions=["s3:PutObject"],
                resources=[f"{self.logs_bucket.bucket_arn}/*"],
            )
        )

        # Static Website Bucket (for future web interface)
        self.static_bucket = s3.Bucket(
            self,
            "StaticBucket",
            bucket_name=None,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            website_index_document="index.html",
            website_error_document="error.html",
        )

        # Outputs
        CfnOutput(
            self,
            "MediaBucketName",
            value=self.media_bucket.bucket_name,
            description="S3 bucket for media files",
            export_name="SecureMediaBucketName"
        )

        CfnOutput(
            self,
            "MediaBucketArn",
            value=self.media_bucket.bucket_arn,
            description="S3 bucket ARN",
            export_name="SecureMediaBucketArn"
        )

        CfnOutput(
            self,
            "StaticBucketName",
            value=self.static_bucket.bucket_name,
            description="S3 bucket for static website",
            export_name="SecureMediaStaticBucketName"
        )

        CfnOutput(
            self,
            "LogsBucketName",
            value=self.logs_bucket.bucket_name,
            description="S3 bucket for access logs",
            export_name="SecureMediaLogsBucketName"
        )
