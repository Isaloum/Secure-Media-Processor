"""
Monitoring Stack - CloudWatch Dashboards, Alarms, SNS
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_rds as rds,
    aws_s3 as s3,
    CfnOutput,
)
from constructs import Construct


class MonitoringStack(Stack):
    """CloudWatch monitoring and alerting"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api: apigw.RestApi,
        auth_function: lambda_.Function,
        file_function: lambda_.Function,
        scan_function: lambda_.Function,
        database: rds.DatabaseInstance,
        media_bucket: s3.Bucket,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS Topic for alerts
        alert_topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name="secure-media-alerts",
            display_name="Secure Media Processor Alerts",
        )

        # Subscribe email to alerts (replace with your email)
        # Uncomment and add your email:
        # alert_topic.add_subscription(
        #     subscriptions.EmailSubscription("your-email@example.com")
        # )

        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name="SecureMediaProcessor",
        )

        # API Gateway Metrics
        api_4xx_metric = api.metric_client_error(
            statistic=cloudwatch.Stats.SUM,
            period=Duration.minutes(5),
        )
        api_5xx_metric = api.metric_server_error(
            statistic=cloudwatch.Stats.SUM,
            period=Duration.minutes(5),
        )
        api_count_metric = api.metric_count(
            statistic=cloudwatch.Stats.SUM,
            period=Duration.minutes(5),
        )
        api_latency_metric = api.metric_latency(
            statistic=cloudwatch.Stats.AVERAGE,
            period=Duration.minutes(5),
        )

        # Lambda Metrics
        def lambda_metrics(function: lambda_.Function):
            return {
                "invocations": function.metric_invocations(
                    statistic=cloudwatch.Stats.SUM,
                    period=Duration.minutes(5),
                ),
                "errors": function.metric_errors(
                    statistic=cloudwatch.Stats.SUM,
                    period=Duration.minutes(5),
                ),
                "duration": function.metric_duration(
                    statistic=cloudwatch.Stats.AVERAGE,
                    period=Duration.minutes(5),
                ),
                "throttles": function.metric_throttles(
                    statistic=cloudwatch.Stats.SUM,
                    period=Duration.minutes(5),
                ),
            }

        auth_metrics = lambda_metrics(auth_function)
        file_metrics = lambda_metrics(file_function)
        scan_metrics = lambda_metrics(scan_function)

        # RDS Metrics
        db_cpu_metric = database.metric_cpu_utilization(
            statistic=cloudwatch.Stats.AVERAGE,
            period=Duration.minutes(5),
        )
        db_connections_metric = database.metric_database_connections(
            statistic=cloudwatch.Stats.AVERAGE,
            period=Duration.minutes(5),
        )
        db_free_storage_metric = database.metric_free_storage_space(
            statistic=cloudwatch.Stats.AVERAGE,
            period=Duration.minutes(5),
        )

        # S3 Metrics
        s3_bucket_size_metric = cloudwatch.Metric(
            namespace="AWS/S3",
            metric_name="BucketSizeBytes",
            dimensions_map={
                "BucketName": media_bucket.bucket_name,
                "StorageType": "StandardStorage",
            },
            statistic=cloudwatch.Stats.AVERAGE,
            period=Duration.days(1),
        )

        # Dashboard Widgets
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="API Gateway - Requests",
                left=[api_count_metric],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="API Gateway - Errors",
                left=[api_4xx_metric, api_5xx_metric],
                width=12,
            ),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="API Gateway - Latency",
                left=[api_latency_metric],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Lambda - Auth Function",
                left=[auth_metrics["invocations"]],
                right=[auth_metrics["errors"], auth_metrics["throttles"]],
                width=12,
            ),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda - File Function",
                left=[file_metrics["invocations"]],
                right=[file_metrics["errors"], file_metrics["throttles"]],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Lambda - Scan Function",
                left=[scan_metrics["invocations"]],
                right=[scan_metrics["errors"], scan_metrics["throttles"]],
                width=12,
            ),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="RDS - CPU Utilization",
                left=[db_cpu_metric],
                width=8,
            ),
            cloudwatch.GraphWidget(
                title="RDS - Database Connections",
                left=[db_connections_metric],
                width=8,
            ),
            cloudwatch.GraphWidget(
                title="RDS - Free Storage",
                left=[db_free_storage_metric],
                width=8,
            ),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="S3 - Bucket Size",
                left=[s3_bucket_size_metric],
                width=24,
            ),
        )

        # CloudWatch Alarms

        # API Gateway 5xx Errors
        api_5xx_alarm = cloudwatch.Alarm(
            self,
            "Api5xxAlarm",
            alarm_name="SecureMedia-API-5xx-Errors",
            metric=api_5xx_metric,
            threshold=50,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        api_5xx_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        # Lambda Errors
        auth_error_alarm = cloudwatch.Alarm(
            self,
            "AuthErrorAlarm",
            alarm_name="SecureMedia-Auth-Lambda-Errors",
            metric=auth_metrics["errors"],
            threshold=10,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        auth_error_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        file_error_alarm = cloudwatch.Alarm(
            self,
            "FileErrorAlarm",
            alarm_name="SecureMedia-File-Lambda-Errors",
            metric=file_metrics["errors"],
            threshold=10,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        file_error_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        # RDS CPU
        db_cpu_alarm = cloudwatch.Alarm(
            self,
            "DbCpuAlarm",
            alarm_name="SecureMedia-RDS-High-CPU",
            metric=db_cpu_metric,
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        db_cpu_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        # RDS Storage
        db_storage_alarm = cloudwatch.Alarm(
            self,
            "DbStorageAlarm",
            alarm_name="SecureMedia-RDS-Low-Storage",
            metric=db_free_storage_metric,
            threshold=2000000000,  # 2GB in bytes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        db_storage_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        # Outputs
        CfnOutput(
            self,
            "DashboardUrl",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={Stack.of(self).region}#dashboards:name={dashboard.dashboard_name}",
            description="CloudWatch Dashboard URL",
        )

        CfnOutput(
            self,
            "AlertTopicArn",
            value=alert_topic.topic_arn,
            description="SNS Alert Topic ARN",
            export_name="SecureMediaAlertTopicArn"
        )
