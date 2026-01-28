#!/bin/bash

# ============================================================================
# Secure Media Processor - Deployment Script
# ============================================================================
# This script deploys the complete SaaS stack to AWS
# Budget: ~$1-10/month using free tier
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================
print_step "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not installed. Install from: https://aws.amazon.com/cli/"
    exit 1
fi
echo "  ✓ AWS CLI installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
echo "  ✓ AWS configured (Account: $AWS_ACCOUNT, Region: $AWS_REGION)"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    print_error "Terraform not installed. Install from: https://terraform.io/downloads"
    exit 1
fi
echo "  ✓ Terraform installed"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js not installed. Install from: https://nodejs.org"
    exit 1
fi
echo "  ✓ Node.js installed ($(node --version))"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not installed"
    exit 1
fi
echo "  ✓ Python installed ($(python3 --version))"

# ============================================================================
# Get Configuration
# ============================================================================
print_step "Configuration"

# Check if terraform.tfvars exists
TERRAFORM_DIR="infrastructure/terraform"
if [ ! -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
    echo ""
    echo "Enter your domain name (e.g., example.com):"
    read -r DOMAIN_NAME

    if [ -z "$DOMAIN_NAME" ]; then
        print_error "Domain name is required"
        exit 1
    fi

    # Create terraform.tfvars
    cat > "$TERRAFORM_DIR/terraform.tfvars" << EOF
domain_name = "$DOMAIN_NAME"
aws_region  = "$AWS_REGION"
environment = "prod"
EOF
    echo "  ✓ Created terraform.tfvars"
else
    echo "  ✓ terraform.tfvars exists"
    DOMAIN_NAME=$(grep domain_name "$TERRAFORM_DIR/terraform.tfvars" | cut -d'"' -f2)
fi

echo ""
echo "  Domain: $DOMAIN_NAME"
echo "  Region: $AWS_REGION"
echo ""
read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# ============================================================================
# Deploy Infrastructure
# ============================================================================
print_step "Deploying AWS infrastructure with Terraform..."

cd "$TERRAFORM_DIR"

# Initialize Terraform
terraform init -upgrade

# Plan
echo ""
echo "Planning infrastructure changes..."
terraform plan -out=tfplan

echo ""
read -p "Apply these changes? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Apply
terraform apply tfplan

# Get outputs
print_step "Getting infrastructure outputs..."
API_URL=$(terraform output -raw api_gateway_url)
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_client_id)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
LAMBDA_FUNCTION=$(terraform output -raw lambda_function_name)

echo "  API URL: $API_URL"
echo "  Cognito Pool: $COGNITO_USER_POOL_ID"
echo "  Frontend Bucket: $FRONTEND_BUCKET"

cd ../..

# ============================================================================
# Deploy API (Lambda)
# ============================================================================
print_step "Deploying API to Lambda..."

cd api

# Create package directory
rm -rf package lambda.zip
mkdir -p package

# Install dependencies
echo "  Installing Python dependencies..."
pip3 install -r requirements.txt -t package/ --quiet

# Copy application code
cp -r app main.py package/

# Create zip
echo "  Creating deployment package..."
cd package
zip -r ../lambda.zip . -q
cd ..

# Deploy to Lambda
echo "  Uploading to Lambda..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION" \
    --zip-file fileb://lambda.zip \
    --no-cli-pager

# Clean up
rm -rf package lambda.zip

echo "  ✓ API deployed"

cd ..

# ============================================================================
# Deploy Frontend
# ============================================================================
print_step "Deploying Frontend..."

cd frontend

# Create .env file
cat > .env << EOF
VITE_API_URL=$API_URL
VITE_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
VITE_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
VITE_AWS_REGION=$AWS_REGION
EOF
echo "  ✓ Created .env"

# Install dependencies
echo "  Installing npm dependencies..."
npm install --silent

# Build
echo "  Building React app..."
npm run build

# Deploy to S3
echo "  Uploading to S3..."
aws s3 sync build/ "s3://$FRONTEND_BUCKET" --delete --no-cli-pager

echo "  ✓ Frontend deployed"

cd ..

# ============================================================================
# Done!
# ============================================================================
echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}                    DEPLOYMENT COMPLETE!                                   ${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo "Your SaaS is now live!"
echo ""
echo "  Frontend:  http://$FRONTEND_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
echo "  API:       $API_URL"
echo ""
echo "Next steps:"
echo "  1. Point your domain ($DOMAIN_NAME) to the S3 bucket or set up CloudFront"
echo "  2. Create a Gumroad product and add your API key to Lambda env vars"
echo "  3. Sign up for an account on your new app!"
echo ""
echo "To view Lambda logs:"
echo "  aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow"
echo ""
echo "Estimated monthly cost: \$1-5 (within free tier)"
echo ""
