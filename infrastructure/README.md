# AWS Infrastructure - Secure Media Processor

This directory contains the AWS CDK infrastructure code for the Secure Media Processor serverless application.

## Architecture

**Serverless Architecture:**
- **API Gateway** - REST API endpoints
- **Lambda** - Serverless compute for API handlers
- **RDS PostgreSQL** - Relational database for user data
- **S3** - Object storage for encrypted files
- **CloudWatch** - Monitoring and logging

**Cost:** ~$150-180/month for production workload

## Project Structure

```
infrastructure/
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # Python dependencies
├── database/
│   └── init.sql                # Database schema initialization
└── stacks/
    ├── network_stack.py        # VPC, subnets, NAT gateway
    ├── database_stack.py       # RDS PostgreSQL, RDS Proxy
    ├── storage_stack.py        # S3 buckets
    ├── compute_stack.py        # Lambda functions
    ├── api_stack.py            # API Gateway configuration
    └── monitoring_stack.py     # CloudWatch dashboards/alarms
```

## Prerequisites

1. **AWS Account** with admin access
2. **AWS CLI** configured
3. **Node.js 18+** and **npm**
4. **Python 3.11+**
5. **AWS CDK** installed globally:
   ```bash
   npm install -g aws-cdk
   ```

## Quick Start

### 1. Install dependencies

```bash
cd infrastructure
pip install -r requirements.txt
```

### 2. Bootstrap CDK (first time only)

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cdk bootstrap aws://$AWS_ACCOUNT_ID/us-east-1
```

### 3. Deploy all stacks

```bash
cdk deploy --all
```

**Deployment time:** ~15-20 minutes

## Stack Details

### Network Stack

Creates:
- VPC with 6 subnets (2 public, 2 private, 2 isolated)
- NAT Gateway for Lambda internet access
- Security groups for Lambda and RDS

**Cost:** ~$32/month (NAT Gateway)

### Database Stack

Creates:
- RDS PostgreSQL 15 (db.t4g.micro)
- RDS Proxy for connection pooling
- Secrets Manager for credentials
- Automated backups (7-day retention)

**Cost:** ~$17/month

### Storage Stack

Creates:
- Media files bucket (encrypted, versioned)
- Static website bucket
- Access logs bucket
- Lifecycle policies for cost optimization

**Cost:** ~$2-10/month (depends on storage)

### Compute Stack

Creates:
- 4 Lambda functions:
  - `secure-media-auth` - User authentication
  - `secure-media-file` - File upload/download
  - `secure-media-scan` - Malware scanning
  - `secure-media-encryption` - File encryption
- Lambda layer for shared dependencies
- IAM roles with least privilege

**Cost:** ~$20/month (10M invocations)

### API Stack

Creates:
- REST API Gateway
- Lambda integrations
- API key and usage plan
- CORS configuration
- Request throttling

**Cost:** ~$35/month (10M requests)

### Monitoring Stack

Creates:
- CloudWatch dashboard
- Alarms for API errors, Lambda errors, RDS CPU/storage
- SNS topic for alerts

**Cost:** ~$10/month

## Deployment Commands

### Deploy all stacks

```bash
cdk deploy --all
```

### Deploy specific stack

```bash
cdk deploy SecureMediaProcessor-prod-Network
```

### View changes before deployment

```bash
cdk diff
```

### Destroy all resources

```bash
cdk destroy --all
```

**Warning:** This deletes all data!

## Post-Deployment

### 1. Initialize database

```bash
# Get RDS endpoint from deployment output
aws cloudformation describe-stacks \
  --stack-name SecureMediaProcessor-prod-Database \
  --query "Stacks[0].Outputs[?OutputKey=='DBProxyEndpoint'].OutputValue" \
  --output text

# Get database password
aws secretsmanager get-secret-value \
  --secret-id secure-media-processor/db-credentials \
  --query SecretString \
  --output text | jq -r .password

# Connect and run init script
psql -h <DB_PROXY_ENDPOINT> -U postgres -d securemedia -f database/init.sql
```

### 2. Test API

```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name SecureMediaProcessor-prod-API \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

# Test registration
curl -X POST $API_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

### 3. Subscribe to alerts

```bash
# Get SNS topic ARN
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name SecureMediaProcessor-prod-Monitoring \
  --query "Stacks[0].Outputs[?OutputKey=='AlertTopicArn'].OutputValue" \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Environment Variables

Set these before deployment:

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=prod  # or dev, staging
```

## Customization

### Change RDS instance size

Edit `stacks/database_stack.py`:

```python
instance_type=ec2.InstanceType.of(
    ec2.InstanceClass.BURSTABLE4_GRAVITON,
    ec2.InstanceSize.SMALL,  # Change from MICRO to SMALL
),
```

### Add more Lambda memory

Edit `stacks/compute_stack.py`:

```python
memory_size=1024,  # Change from 512 to 1024 MB
```

### Enable Multi-AZ RDS

Edit `stacks/database_stack.py`:

```python
multi_az=True,  # Change from False to True
```

**Note:** This doubles RDS cost (~$34/month)

## Monitoring

### View CloudWatch dashboard

```bash
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SecureMediaProcessor"
```

### View Lambda logs

```bash
aws logs tail /aws/lambda/secure-media-auth --follow
```

### Check alarms

```bash
aws cloudwatch describe-alarms --alarm-name-prefix "SecureMedia-"
```

## Troubleshooting

### CDK deploy fails with "AccessDenied"

Ensure AWS credentials have sufficient permissions:

```bash
aws sts get-caller-identity
```

User needs CloudFormation, Lambda, RDS, S3, IAM permissions.

### Lambda function errors

Check logs:

```bash
aws logs tail /aws/lambda/secure-media-auth --follow
```

Common issues:
- Missing dependencies
- Database connection timeout (use RDS Proxy endpoint)
- VPC misconfiguration

### RDS connection timeout

Ensure Lambda uses RDS Proxy endpoint (not direct RDS endpoint):

```python
os.environ["DB_PROXY_ENDPOINT"]  # Correct
os.environ["DB_ENDPOINT"]         # Wrong
```

## Cost Optimization

### For low traffic (<1000 users):

- Remove Lambda provisioned concurrency
- Use db.t4g.micro RDS
- Disable RDS Proxy

**Cost:** ~$130/month

### For high traffic (>50,000 users):

- Switch to DynamoDB instead of RDS
- Add CloudFront CDN
- Enable Lambda provisioned concurrency

**Cost:** ~$200/month

## CI/CD

GitHub Actions workflow in `.github/workflows/deploy-aws.yml` automates:

1. Run tests
2. Deploy CDK stacks
3. Run smoke tests
4. Clean old Lambda versions

### Required secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## Security

- **VPC:** Lambda and RDS in private subnets
- **Encryption:** S3 and RDS encrypted at rest
- **Secrets:** Credentials in Secrets Manager
- **IAM:** Least privilege roles
- **HTTPS:** API Gateway enforces TLS 1.3

## Support

- **CDK Docs:** https://docs.aws.amazon.com/cdk/
- **AWS Support:** https://console.aws.amazon.com/support/
- **GitHub Issues:** https://github.com/Isaloum/Secure-Media-Processor/issues

## License

MIT License - See LICENSE file
