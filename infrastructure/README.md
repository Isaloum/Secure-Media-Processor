# Infrastructure

AWS infrastructure for Secure Media Processor using Terraform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Cloud ($1-10/month)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Route 53   │────▶│  CloudFront  │────▶│  S3 Frontend │        │
│  │   (Domain)   │     │   (CDN)      │     │  (React App) │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                                                           │
│         │              ┌──────────────┐     ┌──────────────┐        │
│         └─────────────▶│ API Gateway  │────▶│    Lambda    │        │
│                        │  (HTTP API)  │     │  (FastAPI)   │        │
│                        └──────────────┘     └──────┬───────┘        │
│                                                    │                │
│           ┌────────────────────────────────────────┼────────┐       │
│           │                                        │        │       │
│           ▼                                        ▼        ▼       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Cognito    │     │   DynamoDB   │     │   S3 Media   │        │
│  │  (Auth)      │     │  (Database)  │     │  (Storage)   │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Cost Breakdown

| Service | Free Tier | Est. Monthly Cost |
|---------|-----------|-------------------|
| Lambda | 1M requests, 400K GB-sec | $0 |
| API Gateway | 1M calls (12 months) | $0-1 |
| DynamoDB | 25GB, 25 RCU/WCU | $0 |
| S3 | 5GB, 20K GET, 2K PUT | $0-2 |
| Cognito | 50K MAU | $0 |
| CloudWatch | 5GB logs | $0-1 |
| **Total** | | **$0-5** |

## Prerequisites

1. AWS CLI installed and configured
2. Terraform >= 1.0.0
3. Domain name (already in Route 53 or to be configured)

## Quick Start

```bash
cd infrastructure/terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your domain

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply infrastructure
terraform apply

# Get output values for frontend/backend config
terraform output frontend_config
terraform output backend_config
```

## Resources Created

### Compute
- **Lambda Function**: Runs FastAPI application
- **API Gateway (HTTP)**: Routes requests to Lambda

### Storage
- **S3 Frontend Bucket**: Static website hosting for React app
- **S3 Media Bucket**: Encrypted storage for user files
- **S3 Lambda Bucket**: Deployment packages

### Database
- **DynamoDB Users Table**: User profiles
- **DynamoDB Files Table**: File metadata
- **DynamoDB Licenses Table**: License keys
- **DynamoDB Usage Table**: API usage tracking

### Authentication
- **Cognito User Pool**: User registration/login
- **Cognito App Clients**: Web and API clients

### Security
- **IAM Roles**: Lambda execution role with least privilege
- **S3 Encryption**: AES-256 server-side encryption
- **CORS Configuration**: Restricted to your domain

## Outputs

After `terraform apply`, you'll get:

```bash
# API endpoint
terraform output api_gateway_url

# Cognito configuration
terraform output cognito_user_pool_id
terraform output cognito_client_id

# S3 buckets
terraform output frontend_bucket_name
terraform output media_bucket_name

# Full frontend config
terraform output frontend_config
```

## Deployment

### Deploy Frontend
```bash
# Build React app
cd frontend && npm run build

# Deploy to S3
aws s3 sync build/ s3://$(terraform output -raw frontend_bucket_name) --delete
```

### Deploy Lambda
```bash
# Package Lambda
cd api && pip install -r requirements.txt -t package/
cp -r *.py package/ && cd package && zip -r ../lambda.zip .

# Update Lambda
aws lambda update-function-code \
  --function-name $(terraform output -raw lambda_function_name) \
  --zip-file fileb://lambda.zip
```

## Cleanup

```bash
# Destroy all resources
terraform destroy

# Note: S3 buckets with objects must be emptied first
aws s3 rm s3://$(terraform output -raw frontend_bucket_name) --recursive
aws s3 rm s3://$(terraform output -raw media_bucket_name) --recursive
```

## Customization

### Change Region
Edit `terraform.tfvars`:
```hcl
aws_region = "eu-west-1"
```

### Add Custom Domain
After applying, configure Route 53:
```bash
# Create A record pointing to API Gateway
# Create A record pointing to S3/CloudFront
```

### Increase Lambda Resources
```hcl
lambda_memory_size = 512  # MB
lambda_timeout     = 60   # seconds
```
