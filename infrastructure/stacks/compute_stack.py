"""
Compute Stack - Lambda Functions, Layers, IAM Roles
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class ComputeStack(Stack):
    """Lambda functions for API endpoints"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        lambda_security_group: ec2.SecurityGroup,
        database: rds.DatabaseInstance,
        db_secret: secretsmanager.Secret,
        media_bucket: s3.Bucket,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda Layer for shared dependencies (boto3, psycopg2, etc.)
        shared_layer = lambda_.LayerVersion(
            self,
            "SharedLayer",
            code=lambda_.Code.from_asset("../lambda/shared"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared dependencies for Lambda functions",
        )

        # Common environment variables for all Lambda functions
        common_env = {
            "DB_SECRET_ARN": db_secret.secret_arn,
            "DB_PROXY_ENDPOINT": database.db_instance_endpoint_address,
            "DB_NAME": "securemedia",
            "MEDIA_BUCKET": media_bucket.bucket_name,
            "AWS_REGION": Stack.of(self).region,
        }

        # 1. Auth Lambda Function (Register, Login, JWT)
        self.auth_function = lambda_.Function(
            self,
            "AuthFunction",
            function_name="secure-media-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../lambda/auth"),
            handler="handler.lambda_handler",
            timeout=Duration.seconds(10),
            memory_size=512,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            environment={
                **common_env,
                "JWT_SECRET_NAME": "secure-media-processor/jwt-secret",
            },
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            reserved_concurrent_executions=100,
        )

        # Grant permissions to Auth Lambda
        db_secret.grant_read(self.auth_function)

        # Create JWT secret
        jwt_secret = secretsmanager.Secret(
            self,
            "JWTSecret",
            secret_name="secure-media-processor/jwt-secret",
            description="JWT signing secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64,
                exclude_characters="\"@/\\ '",
            ),
        )
        jwt_secret.grant_read(self.auth_function)

        # 2. File Processing Lambda Function (Upload, Download)
        self.file_function = lambda_.Function(
            self,
            "FileFunction",
            function_name="secure-media-file",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../lambda/file_processing"),
            handler="handler.lambda_handler",
            timeout=Duration.seconds(30),
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            reserved_concurrent_executions=50,
        )

        # Grant permissions to File Lambda
        db_secret.grant_read(self.file_function)
        media_bucket.grant_read_write(self.file_function)

        # 3. Malware Scan Lambda Function
        self.scan_function = lambda_.Function(
            self,
            "ScanFunction",
            function_name="secure-media-scan",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../lambda/malware_scan"),
            handler="handler.lambda_handler",
            timeout=Duration.seconds(60),
            memory_size=2048,  # More memory for malware scanning
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            reserved_concurrent_executions=10,
        )

        # Grant permissions to Scan Lambda
        db_secret.grant_read(self.scan_function)
        media_bucket.grant_read(self.scan_function)

        # 4. Encryption Lambda Function (Encrypt/Decrypt)
        self.encryption_function = lambda_.Function(
            self,
            "EncryptionFunction",
            function_name="secure-media-encryption",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../lambda/encryption"),
            handler="handler.lambda_handler",
            timeout=Duration.seconds(30),
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            reserved_concurrent_executions=50,
        )

        # Grant permissions to Encryption Lambda
        db_secret.grant_read(self.encryption_function)
        media_bucket.grant_read_write(self.encryption_function)

        # Outputs
        CfnOutput(
            self,
            "AuthFunctionArn",
            value=self.auth_function.function_arn,
            description="Auth Lambda function ARN",
            export_name="SecureMediaAuthFunctionArn"
        )

        CfnOutput(
            self,
            "FileFunctionArn",
            value=self.file_function.function_arn,
            description="File Lambda function ARN",
            export_name="SecureMediaFileFunctionArn"
        )

        CfnOutput(
            self,
            "ScanFunctionArn",
            value=self.scan_function.function_arn,
            description="Scan Lambda function ARN",
            export_name="SecureMediaScanFunctionArn"
        )

        CfnOutput(
            self,
            "EncryptionFunctionArn",
            value=self.encryption_function.function_arn,
            description="Encryption Lambda function ARN",
            export_name="SecureMediaEncryptionFunctionArn"
        )
