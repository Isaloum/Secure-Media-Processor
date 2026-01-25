#!/usr/bin/env python3
"""
AWS CDK App - Secure Media Processor
Serverless Architecture: Lambda + API Gateway + RDS + S3
"""
import os
from aws_cdk import App, Environment, Tags
from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack
from stacks.monitoring_stack import MonitoringStack

# Environment configuration
AWS_ACCOUNT = os.environ.get("CDK_DEFAULT_ACCOUNT")
AWS_REGION = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "prod")

app = App()

# Define environment
env = Environment(account=AWS_ACCOUNT, region=AWS_REGION)

# Stack naming prefix
stack_prefix = f"SecureMediaProcessor-{ENVIRONMENT}"

# 1. Network Stack (VPC, Subnets, NAT Gateway, Security Groups)
network_stack = NetworkStack(
    app,
    f"{stack_prefix}-Network",
    env=env,
    description="VPC and networking infrastructure for Secure Media Processor"
)

# 2. Database Stack (RDS PostgreSQL, Secrets Manager, RDS Proxy)
database_stack = DatabaseStack(
    app,
    f"{stack_prefix}-Database",
    vpc=network_stack.vpc,
    lambda_security_group=network_stack.lambda_security_group,
    env=env,
    description="RDS PostgreSQL database and connection pooling"
)
database_stack.add_dependency(network_stack)

# 3. Storage Stack (S3 Buckets with encryption and lifecycle policies)
storage_stack = StorageStack(
    app,
    f"{stack_prefix}-Storage",
    env=env,
    description="S3 buckets for file storage and static content"
)

# 4. Compute Stack (Lambda Functions, Layers, IAM Roles)
compute_stack = ComputeStack(
    app,
    f"{stack_prefix}-Compute",
    vpc=network_stack.vpc,
    lambda_security_group=network_stack.lambda_security_group,
    database=database_stack.database,
    db_secret=database_stack.db_secret,
    media_bucket=storage_stack.media_bucket,
    env=env,
    description="Lambda functions for API endpoints"
)
compute_stack.add_dependency(network_stack)
compute_stack.add_dependency(database_stack)
compute_stack.add_dependency(storage_stack)

# 5. API Stack (API Gateway, Lambda Integrations, CORS, Throttling)
api_stack = ApiStack(
    app,
    f"{stack_prefix}-API",
    auth_function=compute_stack.auth_function,
    file_function=compute_stack.file_function,
    scan_function=compute_stack.scan_function,
    encryption_function=compute_stack.encryption_function,
    env=env,
    description="API Gateway with Lambda integrations"
)
api_stack.add_dependency(compute_stack)

# 6. Monitoring Stack (CloudWatch Dashboards, Alarms, SNS)
monitoring_stack = MonitoringStack(
    app,
    f"{stack_prefix}-Monitoring",
    api=api_stack.api,
    auth_function=compute_stack.auth_function,
    file_function=compute_stack.file_function,
    scan_function=compute_stack.scan_function,
    database=database_stack.database,
    media_bucket=storage_stack.media_bucket,
    env=env,
    description="CloudWatch monitoring and alerting"
)
monitoring_stack.add_dependency(api_stack)

# Add tags to all resources
Tags.of(app).add("Project", "SecureMediaProcessor")
Tags.of(app).add("Environment", ENVIRONMENT)
Tags.of(app).add("ManagedBy", "CDK")

app.synth()
