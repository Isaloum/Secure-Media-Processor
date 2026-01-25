# Deployment Guide - Secure Media Processor
## AWS Serverless Architecture (Lambda + API Gateway + RDS + S3)

This guide walks you through deploying the Secure Media Processor to AWS using AWS CDK.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Setup Instructions](#setup-instructions)
4. [Deploy to AWS](#deploy-to-aws)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Testing the API](#testing-the-api)
7. [Monitoring](#monitoring)
8. [Cost Estimate](#cost-estimate)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

1. **AWS Account** with administrative access
2. **AWS CLI** configured with credentials
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)
   ```

3. **Node.js 18+** for AWS CDK
   ```bash
   node --version  # Should be 18.x or higher
   npm --version
   ```

4. **Python 3.11+** for Lambda functions
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

5. **AWS CDK** installed globally
   ```bash
   npm install -g aws-cdk
   cdk --version  # Should be 2.136.0 or higher
   ```

### AWS Credentials

Ensure your AWS credentials are configured:

```bash
# Verify credentials
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

---

## Architecture Overview

**Deployed Resources:**
- 1x VPC with 6 subnets (2 public, 2 private, 2 database)
- 1x NAT Gateway
- 1x RDS PostgreSQL (db.t4g.micro)
- 1x RDS Proxy for connection pooling
- 4x Lambda functions (Auth, File, Scan, Encryption)
- 1x API Gateway REST API
- 3x S3 buckets (media, static, logs)
- CloudWatch dashboards and alarms
- Secrets Manager for credentials

**Monthly Cost:** ~$150-180 (see [Cost Estimate](#cost-estimate))

---

## Setup Instructions

### 1. Clone and Navigate to Infrastructure

```bash
cd /home/user/Secure-Media-Processor
```

### 2. Install CDK Dependencies

```bash
cd infrastructure
pip install -r requirements.txt
```

### 3. Install Lambda Dependencies

Each Lambda function needs its dependencies packaged:

```bash
# Auth function
cd ../lambda/auth
pip install -r requirements.txt -t .

# File processing function
cd ../file_processing
pip install -r requirements.txt -t .

# Malware scan function
cd ../malware_scan
pip install -r requirements.txt -t .

# Encryption function
cd ../encryption
pip install -r requirements.txt -t .

# Shared layer
cd ../shared
pip install -r requirements.txt -t .
```

**Important:** Lambda functions must have dependencies in the same directory for deployment.

### 4. Bootstrap CDK (First Time Only)

```bash
cd ../../infrastructure

# Bootstrap CDK for your AWS account and region
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# Replace ACCOUNT-ID with your actual AWS account ID
# Example: cdk bootstrap aws://123456789012/us-east-1
```

Output:
```
✅  Environment aws://123456789012/us-east-1 bootstrapped
```

---

## Deploy to AWS

### Option 1: Deploy All Stacks at Once

```bash
cd infrastructure
cdk deploy --all --require-approval never
```

This will deploy all 6 stacks:
1. Network Stack (VPC, subnets, NAT gateway)
2. Database Stack (RDS PostgreSQL)
3. Storage Stack (S3 buckets)
4. Compute Stack (Lambda functions)
5. API Stack (API Gateway)
6. Monitoring Stack (CloudWatch)

**Deployment Time:** ~15-20 minutes

### Option 2: Deploy Stacks Individually

```bash
# 1. Network infrastructure
cdk deploy SecureMediaProcessor-prod-Network

# 2. Database (depends on network)
cdk deploy SecureMediaProcessor-prod-Database

# 3. Storage (independent)
cdk deploy SecureMediaProcessor-prod-Storage

# 4. Lambda functions (depends on network, database, storage)
cdk deploy SecureMediaProcessor-prod-Compute

# 5. API Gateway (depends on compute)
cdk deploy SecureMediaProcessor-prod-API

# 6. Monitoring (depends on API)
cdk deploy SecureMediaProcessor-prod-Monitoring
```

### Deployment Output

After successful deployment, you'll see:

```
✅  SecureMediaProcessor-prod-Network
✅  SecureMediaProcessor-prod-Database
✅  SecureMediaProcessor-prod-Storage
✅  SecureMediaProcessor-prod-Compute
✅  SecureMediaProcessor-prod-API
✅  SecureMediaProcessor-prod-Monitoring

Outputs:
SecureMediaProcessor-prod-API.ApiUrl = https://abcd1234.execute-api.us-east-1.amazonaws.com/prod/
SecureMediaProcessor-prod-Database.DBProxyEndpoint = secure-media-proxy.proxy-xxxxx.us-east-1.rds.amazonaws.com
SecureMediaProcessor-prod-Storage.MediaBucketName = securemediaprocessor-prod-mediabucket-xxxxx
```

**Save these outputs!** You'll need them for testing.

---

## Post-Deployment Configuration

### 1. Initialize Database

Connect to RDS and run the initialization script:

```bash
# Get database credentials from Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id secure-media-processor/db-credentials \
  --query SecretString \
  --output text

# Connect to RDS (use the proxy endpoint from deployment output)
psql -h secure-media-proxy.proxy-xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d securemedia

# Run initialization script
\i infrastructure/database/init.sql

# Verify tables created
\dt

# Expected output:
#           List of relations
#  Schema |    Name    | Type  |  Owner
# --------+------------+-------+----------
#  public | api_keys   | table | postgres
#  public | audit_logs | table | postgres
#  public | files      | table | postgres
#  public | users      | table | postgres
```

### 2. Configure Email Alerts (Optional)

Subscribe to SNS topic for CloudWatch alarms:

```bash
# Get SNS topic ARN from deployment output
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:secure-media-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription in your email inbox
```

### 3. Configure CORS (Optional)

Update API Gateway CORS settings for your frontend domain:

Edit `infrastructure/stacks/api_stack.py`:

```python
default_cors_preflight_options=apigw.CorsOptions(
    allow_origins=["https://yourdomain.com"],  # Change from "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
),
```

Redeploy:

```bash
cdk deploy SecureMediaProcessor-prod-API
```

---

## Testing the API

### 1. Get API URL

```bash
# From deployment output or CloudFormation
aws cloudformation describe-stacks \
  --stack-name SecureMediaProcessor-prod-API \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text
```

Example: `https://abcd1234.execute-api.us-east-1.amazonaws.com/prod/`

### 2. Test User Registration

```bash
curl -X POST https://YOUR-API-URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'

# Expected response:
# {
#   "success": true,
#   "data": {
#     "message": "User registered successfully",
#     "email": "test@example.com"
#   }
# }
```

### 3. Test User Login

```bash
curl -X POST https://YOUR-API-URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'

# Expected response:
# {
#   "success": true,
#   "data": {
#     "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     "user": {
#       "id": "123e4567-e89b-12d3-a456-426614174000",
#       "email": "test@example.com"
#     }
#   }
# }
```

### 4. Test File Upload (Presigned URL)

```bash
# Get upload URL
TOKEN="<your-jwt-token-from-login>"

curl -X POST https://YOUR-API-URL/api/v1/files \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "filename": "test.txt",
    "file_size": 1024,
    "mime_type": "text/plain"
  }'

# Response includes presigned URL for direct S3 upload
```

### 5. Test Health Check

```bash
# Check Lambda function logs
aws logs tail /aws/lambda/secure-media-auth --follow
```

---

## Monitoring

### CloudWatch Dashboard

View the monitoring dashboard:

```bash
# Open in browser (replace REGION with your region)
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SecureMediaProcessor
```

**Metrics displayed:**
- API Gateway requests, errors, latency
- Lambda invocations, errors, duration
- RDS CPU, connections, storage
- S3 bucket size

### CloudWatch Alarms

Check alarm status:

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "SecureMedia-"
```

**Configured alarms:**
- API 5xx errors > 50 in 5 minutes
- Lambda errors > 10 per function
- RDS CPU > 80%
- RDS storage < 2GB remaining

### View Logs

```bash
# Lambda function logs
aws logs tail /aws/lambda/secure-media-auth --follow
aws logs tail /aws/lambda/secure-media-file --follow
aws logs tail /aws/lambda/secure-media-scan --follow

# API Gateway access logs
aws logs tail /aws/apigateway/secure-media-processor --follow
```

---

## Cost Estimate

### Monthly Cost Breakdown (10,000 users, 100k files)

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| API Gateway | 10M requests | $35.00 |
| Lambda | 10M invocations (512MB avg) | $20.00 |
| RDS PostgreSQL | db.t4g.micro | $15.00 |
| RDS Proxy | Connection pooling | $15.00 |
| RDS Storage | 20GB gp3 | $2.00 |
| S3 Storage | 100GB | $2.30 |
| S3 Requests | 1M PUT, 10M GET | $10.00 |
| NAT Gateway | VPC internet access | $32.00 |
| Secrets Manager | 5 secrets | $2.00 |
| CloudWatch | 5GB logs, 10 metrics | $10.00 |
| Data Transfer | Outbound | $9.00 |
| **TOTAL** | | **~$152.30** |

### Cost Optimization Tips

**For low traffic (<1000 users):**
- Remove Lambda provisioned concurrency: -$10/month
- Use smaller RDS instance: -$8/month
- **New total: ~$134/month**

**For high traffic (>50,000 users):**
- Switch to DynamoDB: -$17 (RDS) + $25 (DynamoDB)
- Add CloudFront CDN: +$20/month
- **Total: ~$190/month**

---

## Troubleshooting

### Issue: CDK Deploy Fails

**Error:** `AccessDenied: User is not authorized`

**Solution:** Ensure AWS credentials have sufficient permissions

```bash
aws iam get-user
aws sts get-caller-identity

# Your user needs these policies:
# - AdministratorAccess (or)
# - Custom policy with CloudFormation, Lambda, RDS, S3, IAM permissions
```

### Issue: Lambda Function Errors

**Error:** `Unable to connect to database`

**Solution:** Check VPC configuration and security groups

```bash
# Verify Lambda is in correct subnets
aws lambda get-function-configuration \
  --function-name secure-media-auth \
  --query 'VpcConfig'

# Verify RDS security group allows Lambda
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --query 'SecurityGroups[0].IpPermissions'
```

### Issue: API Gateway 502 Errors

**Error:** `{"message":"Internal server error"}`

**Solution:** Check Lambda function logs

```bash
aws logs tail /aws/lambda/secure-media-auth --follow
```

Common causes:
- Missing dependencies in Lambda package
- Database connection timeout
- Lambda timeout (increase to 30s)

### Issue: Database Connection Timeout

**Error:** `psycopg2.OperationalError: timeout expired`

**Solution:** Use RDS Proxy endpoint instead of direct RDS endpoint

```python
# Correct:
DB_ENDPOINT = os.environ["DB_PROXY_ENDPOINT"]

# Incorrect:
DB_ENDPOINT = "database.xxxxx.us-east-1.rds.amazonaws.com"
```

### Issue: S3 Upload Fails

**Error:** `Access Denied`

**Solution:** Verify Lambda has S3 permissions

```bash
aws iam get-role-policy \
  --role-name SecureMediaProcessor-prod-Compute-FileFunctionRole \
  --policy-name S3Access
```

---

## Rollback

To remove all resources:

```bash
cd infrastructure

# Delete all stacks (in reverse order)
cdk destroy --all

# Or delete individually
cdk destroy SecureMediaProcessor-prod-Monitoring
cdk destroy SecureMediaProcessor-prod-API
cdk destroy SecureMediaProcessor-prod-Compute
cdk destroy SecureMediaProcessor-prod-Storage
cdk destroy SecureMediaProcessor-prod-Database
cdk destroy SecureMediaProcessor-prod-Network
```

**Warning:** This will delete:
- All uploaded files in S3
- All user data in RDS (unless you have snapshots)
- All CloudWatch logs

---

## Next Steps

1. **Set up CI/CD** - Automate deployment with GitHub Actions
2. **Add custom domain** - Configure Route53 and CloudFront
3. **Enable WAF** - Add DDoS protection and rate limiting
4. **Production hardening** - Enable Multi-AZ RDS, add read replicas
5. **Implement JWT validation** - Complete authentication flow in Lambda authorizers
6. **Add monitoring** - Integrate with DataDog or New Relic

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/Isaloum/Secure-Media-Processor/issues
- AWS Support: https://console.aws.amazon.com/support/

---

## Summary

✅ **Deployed:** Serverless architecture with Lambda, API Gateway, RDS, S3
✅ **Cost:** ~$150/month for production workload
✅ **Scalability:** Auto-scales to handle 10,000+ concurrent users
✅ **Security:** VPC isolation, encryption at rest/transit, IAM least privilege
✅ **Monitoring:** CloudWatch dashboards, alarms, and logs

**Deployment time:** 15-20 minutes
**Break-even:** 10 paying users at $15/month
