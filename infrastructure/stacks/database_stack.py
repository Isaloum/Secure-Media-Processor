"""
Database Stack - RDS PostgreSQL, Secrets Manager, RDS Proxy
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Database infrastructure with RDS PostgreSQL"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        lambda_security_group: ec2.SecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Database credentials secret
        self.db_secret = secretsmanager.Secret(
            self,
            "DBSecret",
            secret_name="secure-media-processor/db-credentials",
            description="RDS PostgreSQL credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_characters="\"@/\\ '",
                password_length=32,
            ),
        )

        # RDS Parameter Group for PostgreSQL optimization
        parameter_group = rds.ParameterGroup(
            self,
            "DBParameterGroup",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_5
            ),
            parameters={
                "shared_preload_libraries": "pg_stat_statements",
                "log_statement": "all",
                "log_min_duration_statement": "1000",  # Log queries > 1s
            },
        )

        # RDS Instance
        self.database = rds.DatabaseInstance(
            self,
            "Database",
            database_name="securemedia",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_5
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                ec2.InstanceSize.MICRO,  # t4g.micro for cost efficiency
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            credentials=rds.Credentials.from_secret(self.db_secret),
            allocated_storage=20,
            max_allocated_storage=100,  # Auto-scaling up to 100GB
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            multi_az=False,  # Set to True for production
            publicly_accessible=False,
            parameter_group=parameter_group,
            backup_retention=Duration.days(7),
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="Mon:04:00-Mon:05:00",
            deletion_protection=False,  # Set to True for production
            removal_policy=RemovalPolicy.SNAPSHOT,  # Create snapshot on deletion
            enable_performance_insights=True,
            performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT,  # 7 days (free tier)
        )

        # Allow Lambda to connect to RDS
        self.database.connections.allow_from(
            lambda_security_group,
            ec2.Port.tcp(5432),
            "Allow Lambda to connect to RDS"
        )

        # RDS Proxy for connection pooling (recommended for Lambda)
        self.db_proxy = rds.DatabaseProxy(
            self,
            "DBProxy",
            proxy_target=rds.ProxyTarget.from_instance(self.database),
            secrets=[self.db_secret],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            db_proxy_name="secure-media-proxy",
            idle_client_timeout=Duration.minutes(30),
            max_connections_percent=90,
            require_tls=True,
        )

        # Outputs
        CfnOutput(
            self,
            "DBEndpoint",
            value=self.database.db_instance_endpoint_address,
            description="RDS endpoint address",
            export_name="SecureMediaDBEndpoint"
        )

        CfnOutput(
            self,
            "DBProxyEndpoint",
            value=self.db_proxy.endpoint,
            description="RDS Proxy endpoint (use this for Lambda)",
            export_name="SecureMediaDBProxyEndpoint"
        )

        CfnOutput(
            self,
            "DBSecretArn",
            value=self.db_secret.secret_arn,
            description="Database secret ARN",
            export_name="SecureMediaDBSecretArn"
        )

        CfnOutput(
            self,
            "DBName",
            value="securemedia",
            description="Database name",
            export_name="SecureMediaDBName"
        )
