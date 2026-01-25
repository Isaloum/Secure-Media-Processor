"""
API Stack - API Gateway REST API with Lambda integrations
"""
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class ApiStack(Stack):
    """API Gateway with Lambda integrations"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        auth_function: lambda_.Function,
        file_function: lambda_.Function,
        scan_function: lambda_.Function,
        encryption_function: lambda_.Function,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudWatch Log Group for API Gateway access logs
        log_group = logs.LogGroup(
            self,
            "ApiGatewayAccessLogs",
            log_group_name="/aws/apigateway/secure-media-processor",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # REST API
        self.api = apigw.RestApi(
            self,
            "SecureMediaApi",
            rest_api_name="Secure Media Processor API",
            description="Serverless API for secure media processing",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=10000,
                throttling_burst_limit=5000,
                logging_level=apigw.MethodLoggingLevel.INFO,
                access_log_destination=apigw.LogGroupLogDestination(log_group),
                access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
                metrics_enabled=True,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=["*"],  # Configure with your domain
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Api-Key",
                ],
            ),
            cloud_watch_role=True,
        )

        # API Key and Usage Plan for rate limiting
        api_key = self.api.add_api_key(
            "ApiKey",
            api_key_name="secure-media-api-key",
        )

        usage_plan = self.api.add_usage_plan(
            "UsagePlan",
            name="Standard",
            throttle=apigw.ThrottleSettings(
                rate_limit=1000,
                burst_limit=2000,
            ),
            quota=apigw.QuotaSettings(
                limit=1000000,
                period=apigw.Period.MONTH,
            ),
        )
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=self.api.deployment_stage)

        # Lambda integrations
        auth_integration = apigw.LambdaIntegration(auth_function)
        file_integration = apigw.LambdaIntegration(file_function)
        scan_integration = apigw.LambdaIntegration(scan_function)
        encryption_integration = apigw.LambdaIntegration(encryption_function)

        # API Resources: /api/v1
        api_v1 = self.api.root.add_resource("api").add_resource("v1")

        # Auth endpoints: /api/v1/auth
        auth_resource = api_v1.add_resource("auth")
        register_resource = auth_resource.add_resource("register")
        login_resource = auth_resource.add_resource("login")

        register_resource.add_method("POST", auth_integration)
        login_resource.add_method("POST", auth_integration)

        # File endpoints: /api/v1/files
        files_resource = api_v1.add_resource("files")
        files_resource.add_method("POST", file_integration)  # Upload
        files_resource.add_method("GET", file_integration)   # List

        file_id_resource = files_resource.add_resource("{id}")
        file_id_resource.add_method("GET", file_integration)    # Download
        file_id_resource.add_method("DELETE", file_integration) # Delete

        # Scan endpoints: /api/v1/scan
        scan_resource = api_v1.add_resource("scan")
        malware_resource = scan_resource.add_resource("malware")
        malware_resource.add_method("POST", scan_integration)

        status_resource = scan_resource.add_resource("status").add_resource("{id}")
        status_resource.add_method("GET", scan_integration)

        # Encryption endpoints: /api/v1/encrypt, /api/v1/decrypt
        encrypt_resource = api_v1.add_resource("encrypt")
        decrypt_resource = api_v1.add_resource("decrypt")

        encrypt_resource.add_method("POST", encryption_integration)
        decrypt_resource.add_method("POST", encryption_integration)

        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name="SecureMediaApiUrl"
        )

        CfnOutput(
            self,
            "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway ID",
            export_name="SecureMediaApiId"
        )

        CfnOutput(
            self,
            "ApiKeyId",
            value=api_key.key_id,
            description="API Key ID",
            export_name="SecureMediaApiKeyId"
        )
