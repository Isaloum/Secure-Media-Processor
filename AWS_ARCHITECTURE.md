# Consolidated AWS Serverless Architecture
## Secure Media Processor - Production SaaS Platform

**Architecture Pattern:** Serverless with RDS
**Cost Target:** $50-150/month (scales with usage)
**Deployment:** AWS CDK (Python)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERNET                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   Amazon Route53 │
                    │   (DNS + Health) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  CloudFront CDN  │
                    │  (SSL/TLS + WAF) │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼─────┐     ┌─────▼──────┐     ┌────▼─────┐
     │   S3     │     │  API       │     │ S3 Static│
     │ (Static) │     │  Gateway   │     │ (Media)  │
     └──────────┘     │  (REST)    │     └──────────┘
                      └─────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         ┌────▼────┐   ┌───▼────┐   ┌───▼────┐
         │ Lambda  │   │ Lambda │   │ Lambda │
         │ (Auth)  │   │ (File) │   │ (Scan) │
         └────┬────┘   └───┬────┘   └───┬────┘
              │            │            │
              └─────────┬──┴────────────┘
                        │
              ┌─────────▼──────────┐
              │    VPC (Private)   │
              │  ┌──────────────┐  │
              │  │ RDS PostgreSQL│  │
              │  │ (Multi-AZ)    │  │
              │  └──────────────┘  │
              └────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  Secrets Manager   │
              │  (Credentials)     │
              └────────────────────┘
                        │
              ┌─────────▼──────────┐
              │   CloudWatch       │
              │  (Logs + Metrics)  │
              └────────────────────┘
```

---

## Component Breakdown

### 1. API Gateway (REST API)

**Purpose:** Serverless API endpoint management

**Configuration:**
- REST API (not HTTP API for cost efficiency)
- Request validation
- Throttling: 10,000 requests/sec
- API keys for client authentication
- Usage plans for rate limiting
- CORS configuration

**Endpoints:**
```
POST   /api/v1/auth/register        → Lambda (Auth)
POST   /api/v1/auth/login           → Lambda (Auth)
POST   /api/v1/files/upload         → Lambda (File Processing)
GET    /api/v1/files/{id}           → Lambda (File Retrieval)
POST   /api/v1/scan/malware         → Lambda (Malware Scan)
GET    /api/v1/scan/status/{id}     → Lambda (Status Check)
POST   /api/v1/encrypt              → Lambda (Encryption)
POST   /api/v1/decrypt              → Lambda (Decryption)
```

**Cost:** ~$3.50/million requests + $0.09/GB data transfer

---

### 2. AWS Lambda Functions

**Architecture:** Python 3.11 runtime

#### **Lambda Function Structure:**

```
lambda/
├── auth/
│   ├── handler.py          # Auth endpoint (register/login)
│   ├── jwt_utils.py        # Token generation
│   └── requirements.txt    # bcrypt, PyJWT
├── file_processing/
│   ├── handler.py          # File upload/download
│   ├── s3_utils.py         # S3 operations
│   └── requirements.txt    # boto3, Pillow
├── malware_scan/
│   ├── handler.py          # Malware scanning
│   ├── scanner.py          # Detection logic
│   └── requirements.txt    # yara-python
├── encryption/
│   ├── handler.py          # Encrypt/decrypt
│   ├── crypto_utils.py     # Cryptography logic
│   └── requirements.txt    # cryptography
└── shared/
    ├── db_utils.py         # RDS connection pooling
    ├── config.py           # Environment config
    └── response.py         # Standard API responses
```

#### **Lambda Configuration:**

| Function | Memory | Timeout | Concurrency | Cold Start |
|----------|--------|---------|-------------|------------|
| Auth | 512 MB | 10s | 100 | ~1s |
| File Processing | 1024 MB | 30s | 50 | ~2s |
| Malware Scan | 2048 MB | 60s | 10 | ~3s |
| Encryption | 1024 MB | 30s | 50 | ~2s |

**Optimizations:**
- Lambda Layers for shared dependencies (boto3, psycopg2)
- Provisioned Concurrency for critical functions (Auth: 2 instances)
- VPC configuration for RDS access
- Environment variables from Secrets Manager

**Cost:** ~$0.20 per 1M requests (512MB, 1s execution)

---

### 3. Amazon RDS PostgreSQL

**Purpose:** User data, file metadata, audit logs

**Configuration:**
- Engine: PostgreSQL 15
- Instance: db.t4g.micro (2 vCPU, 1GB RAM)
- Storage: 20GB gp3 (scalable to 100GB)
- Multi-AZ: No (enable for production)
- Backup: 7-day retention
- Encryption: AES-256 at rest
- VPC: Private subnet (no public access)

**Database Schema:**

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    storage_used_bytes BIGINT DEFAULT 0
);

-- Files table
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    s3_key VARCHAR(512) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    encryption_algorithm VARCHAR(50),
    checksum_sha256 VARCHAR(64),
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    malware_scan_status VARCHAR(50) DEFAULT 'pending',
    malware_scan_result JSONB,
    metadata JSONB
);

-- Audit logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT NOW(),
    details JSONB
);

-- Indexes
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_upload_timestamp ON files(upload_timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

**Connection Pooling:**
- Use RDS Proxy for Lambda connection pooling
- Reduces cold start connection overhead
- Cost: ~$15/month

**Cost:** ~$15/month (db.t4g.micro) + ~$2/month (20GB storage)

---

### 4. Amazon S3

**Purpose:** File storage with encryption

**Bucket Structure:**

```
secure-media-processor-prod/
├── uploads/                    # User uploaded files
│   ├── {user_id}/
│   │   └── {file_id}.encrypted
├── processed/                  # Processed media
│   └── {user_id}/
│       └── {file_id}.processed
├── static/                     # Static website assets
│   ├── index.html
│   ├── css/
│   └── js/
└── logs/                       # Access logs
    └── {date}/
```

**Configuration:**
- Versioning: Enabled
- Encryption: AES-256 (SSE-S3)
- Lifecycle Policy:
  - Delete temp files after 7 days
  - Move to Glacier after 90 days (optional)
- CORS: Configured for web uploads
- Block Public Access: Enabled
- Replication: Optional (cross-region)

**Presigned URLs:**
- Lambda generates presigned URLs for uploads
- Expires in 15 minutes
- Client uploads directly to S3 (no Lambda proxy)

**Cost:** ~$0.023/GB/month + $0.005/1000 PUT requests

---

### 5. VPC Configuration

**Purpose:** Isolate RDS and Lambda in private network

**Network Design:**

```
VPC: 10.0.0.0/16 (secure-media-vpc)
├── Public Subnets (NAT Gateway)
│   ├── 10.0.1.0/24 (us-east-1a)
│   └── 10.0.2.0/24 (us-east-1b)
├── Private Subnets (Lambda + RDS)
│   ├── 10.0.10.0/24 (us-east-1a) → Lambda
│   └── 10.0.11.0/24 (us-east-1b) → RDS
└── Database Subnets
    ├── 10.0.20.0/24 (us-east-1a)
    └── 10.0.21.0/24 (us-east-1b)
```

**Security Groups:**

```python
# Lambda Security Group
lambda_sg:
  - Outbound: ALL (for internet access via NAT)
  - Inbound: None

# RDS Security Group
rds_sg:
  - Inbound: Port 5432 from lambda_sg only
  - Outbound: None
```

**Cost:** ~$0.045/hour NAT Gateway (~$32/month)

---

### 6. AWS Secrets Manager

**Purpose:** Store sensitive credentials

**Secrets:**

```json
{
  "db_password": "rds-postgres-password",
  "jwt_secret": "jwt-signing-key",
  "api_keys": {
    "malware_scan_api": "external-api-key"
  }
}
```

**Lambda Integration:**

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Use in Lambda
secrets = get_secret('prod/secure-media-processor')
db_password = secrets['db_password']
```

**Cost:** $0.40/month per secret + $0.05 per 10,000 API calls

---

### 7. CloudWatch Monitoring

**Logs:**
- Lambda execution logs (7-day retention)
- API Gateway access logs
- RDS slow query logs

**Metrics:**
- Lambda invocations, errors, duration
- API Gateway latency, 4xx/5xx errors
- RDS CPU, connections, storage

**Alarms:**

```yaml
Alarms:
  - Lambda errors > 10 in 5 minutes → SNS email
  - API Gateway 5xx > 50 in 5 minutes → SNS email
  - RDS CPU > 80% for 10 minutes → SNS email
  - RDS storage < 20% remaining → SNS email
```

**Cost:** ~$10/month (5GB logs, 10 metrics, 5 alarms)

---

## Security Architecture

### 1. Authentication & Authorization

**JWT-based Authentication:**

```python
# Lambda Auth Function
import jwt
import bcrypt
from datetime import datetime, timedelta

def register_user(email, password):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    # Store in RDS
    return {"user_id": user_id}

def login(email, password):
    # Verify password from RDS
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, JWT_SECRET, algorithm='HS256')
    return {"token": token}
```

**API Gateway Authorization:**
- Lambda authorizer validates JWT
- Caches authorization for 5 minutes
- Returns IAM policy with allowed resources

### 2. Encryption

**Data at Rest:**
- S3: SSE-S3 (AES-256)
- RDS: Encrypted storage volumes
- Secrets Manager: KMS encryption

**Data in Transit:**
- CloudFront → API Gateway: TLS 1.3
- Lambda → RDS: TLS (PostgreSQL SSL)
- Lambda → S3: HTTPS

**Application-Level Encryption:**
- Client encrypts files before upload (optional)
- Lambda re-encrypts with KMS (optional)

### 3. IAM Roles

**Lambda Execution Roles:**

```yaml
LambdaAuthRole:
  - RDS: Connect, Query (users table)
  - Secrets Manager: GetSecretValue
  - CloudWatch: PutLogEvents

LambdaFileRole:
  - S3: GetObject, PutObject (user prefix only)
  - RDS: Connect, Query (files table)
  - Secrets Manager: GetSecretValue
  - CloudWatch: PutLogEvents

LambdaScanRole:
  - S3: GetObject
  - RDS: Connect, UpdateRecord
  - Secrets Manager: GetSecretValue
  - CloudWatch: PutLogEvents
```

**Least Privilege Principle:**
- No wildcard permissions
- Resource-based policies
- Condition-based access

### 4. DDoS Protection

**AWS Shield Standard:** Free (automatic)
**AWS WAF Rules:**
- Rate limiting: 100 requests/5 minutes per IP
- Geo-blocking: Block high-risk countries (optional)
- SQL injection protection
- XSS protection

**Cost:** ~$5/month (WAF base) + $1/rule

---

## Cost Analysis

### Monthly Cost Breakdown (Expected Traffic: 10,000 users, 100k files)

| Service | Configuration | Monthly Cost | Notes |
|---------|---------------|--------------|-------|
| **API Gateway** | 10M requests/month | $35.00 | $3.50/million |
| **Lambda** | 10M invocations, 512MB avg | $20.00 | $0.20/million (includes compute) |
| **Lambda (Provisioned)** | 2 instances x Auth | $10.00 | Reduce cold starts |
| **RDS** | db.t4g.micro (1GB RAM) | $15.00 | PostgreSQL 15 |
| **RDS Proxy** | Connection pooling | $15.00 | Recommended for Lambda |
| **RDS Storage** | 20GB gp3 | $2.00 | $0.10/GB |
| **S3 Storage** | 100GB files | $2.30 | $0.023/GB |
| **S3 Requests** | 1M PUT, 10M GET | $10.00 | Uploads + downloads |
| **NAT Gateway** | VPC internet access | $32.00 | $0.045/hour + data |
| **Secrets Manager** | 5 secrets | $2.00 | $0.40/secret |
| **CloudWatch** | 5GB logs, 10 metrics | $10.00 | 7-day retention |
| **Route53** | 1 hosted zone | $0.50 | DNS |
| **CloudFront** | 100GB transfer | $8.50 | CDN |
| **WAF** | Basic rules | $6.00 | DDoS protection |
| **Data Transfer** | Outbound (S3/Lambda) | $9.00 | $0.09/GB |
| **Backups** | RDS automated backups | $2.00 | 7-day retention |
| **TOTAL** | | **~$179.30** | |

### Cost Optimization Strategies

**For Low Traffic (<1000 users):**
- Remove Provisioned Concurrency: -$10/month
- Use RDS t4g.micro without RDS Proxy: -$15/month
- Reduce CloudWatch retention to 3 days: -$5/month
- **New Total: ~$149/month**

**For High Traffic (>50,000 users):**
- Move to DynamoDB instead of RDS: -$17/month (RDS) + $25/month (DynamoDB) = +$8/month
- Enable Lambda provisioned concurrency for all: +$30/month
- Add CloudFront caching: -$15/month (reduced API calls)
- **Scales to ~$200/month at 50k users**

---

## Deployment Strategy

### Infrastructure as Code (AWS CDK)

**Project Structure:**

```
infrastructure/
├── cdk.json                    # CDK config
├── requirements.txt            # CDK dependencies
├── app.py                      # CDK app entry point
└── stacks/
    ├── __init__.py
    ├── network_stack.py        # VPC, subnets, NAT
    ├── database_stack.py       # RDS, Secrets Manager
    ├── storage_stack.py        # S3 buckets
    ├── compute_stack.py        # Lambda functions
    ├── api_stack.py            # API Gateway
    ├── monitoring_stack.py     # CloudWatch, alarms
    └── cdn_stack.py            # CloudFront, Route53
```

**CDK Bootstrap:**

```bash
# Install CDK
npm install -g aws-cdk

# Bootstrap CDK (one-time)
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy SecureMediaProcessor-NetworkStack
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install -g aws-cdk

      - name: Run tests
        run: pytest tests/

      - name: Deploy CDK stacks
        run: cdk deploy --all --require-approval never

      - name: Run smoke tests
        run: pytest tests/integration/
```

---

## Migration Plan

### Phase 1: Infrastructure Setup (Week 1)

1. Create VPC and networking
2. Deploy RDS PostgreSQL
3. Configure Secrets Manager
4. Set up S3 buckets

### Phase 2: Lambda Development (Week 2)

1. Migrate CLI logic to Lambda functions
2. Create shared layers (boto3, psycopg2)
3. Implement API endpoints
4. Add RDS connection pooling

### Phase 3: API Gateway (Week 3)

1. Configure REST API
2. Add Lambda integrations
3. Set up authentication
4. Configure CORS and throttling

### Phase 4: Monitoring & Security (Week 4)

1. Configure CloudWatch alarms
2. Add WAF rules
3. Set up CloudFront CDN
4. Enable RDS backups

### Phase 5: Testing & Launch (Week 5)

1. Load testing (Artillery, k6)
2. Security testing (OWASP ZAP)
3. Performance optimization
4. Production launch

---

## Scaling Strategy

### Horizontal Scaling (Automatic)

**Lambda:**
- Auto-scales to 1000 concurrent executions
- Add reserved concurrency for critical functions
- Use SQS for async processing (optional)

**RDS:**
- Vertical scaling: db.t4g.micro → db.t4g.small (2GB RAM)
- Read replicas for high-read workloads
- Aurora Serverless v2 for extreme scaling (optional)

**API Gateway:**
- Auto-scales to handle traffic
- Add caching for frequently accessed endpoints
- Use CloudFront for global distribution

### When to Upgrade

| Metric | Threshold | Action |
|--------|-----------|--------|
| RDS CPU | >70% sustained | Upgrade to t4g.small |
| Lambda errors | >5% error rate | Add provisioned concurrency |
| API latency | >500ms p95 | Enable CloudFront caching |
| S3 costs | >$100/month | Implement lifecycle policies |

---

## Disaster Recovery

### Backup Strategy

**RDS:**
- Automated daily backups (7-day retention)
- Manual snapshots before major changes
- Point-in-time recovery enabled

**S3:**
- Versioning enabled
- Cross-region replication (optional)
- MFA delete protection

**Recovery Time Objective (RTO):** 4 hours
**Recovery Point Objective (RPO):** 24 hours

### Rollback Procedure

```bash
# Rollback CDK deployment
cdk deploy --rollback

# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier secure-media-prod \
  --db-snapshot-identifier prod-snapshot-2024-01-01

# Restore S3 from versioning
aws s3api list-object-versions --bucket secure-media-prod
aws s3api get-object --version-id {VERSION_ID}
```

---

## Monitoring & Alerting

### Key Metrics

**Application:**
- File uploads per minute
- Malware detections per hour
- Active users (DAU/MAU)
- API error rates

**Infrastructure:**
- Lambda cold starts
- RDS connection count
- S3 storage growth rate
- API Gateway latency

### Dashboards

**CloudWatch Dashboard:**
```
┌─────────────────────────────────────────┐
│  API Gateway: Requests/sec, Latency     │
├─────────────────────────────────────────┤
│  Lambda: Invocations, Errors, Duration  │
├─────────────────────────────────────────┤
│  RDS: CPU, Connections, IOPS            │
├─────────────────────────────────────────┤
│  S3: Storage, Requests, Errors          │
└─────────────────────────────────────────┘
```

---

## Security Compliance

### Compliance Frameworks

**SOC 2 Type II Ready:**
- Encryption at rest and in transit
- Audit logging (CloudTrail + RDS logs)
- Access controls (IAM roles)
- Backup and disaster recovery

**GDPR Considerations:**
- Right to deletion (S3 lifecycle + RDS CASCADE)
- Data portability (export API)
- Consent management (user preferences table)
- Data residency (region selection)

**HIPAA Considerations (if applicable):**
- Use AWS HIPAA-eligible services
- Sign BAA with AWS
- Enable encryption everywhere
- PHI data segregation

---

## Next Steps

1. **Review this architecture** - Approve or suggest changes
2. **Create CDK code** - Infrastructure as Code
3. **Develop Lambda functions** - Migrate CLI logic
4. **Set up CI/CD** - Automated deployment
5. **Launch MVP** - Deploy to production

**Estimated Total Effort:** 4-5 weeks (1 developer)

**Break-even Analysis:**
- Monthly cost: ~$150
- Revenue per user: $15/month (Standard plan)
- Break-even: 10 paying users

---

## Summary

This serverless architecture provides:

✅ **Cost Efficiency:** ~$150/month (vs $300+ with ECS)
✅ **Auto-scaling:** Lambda handles traffic spikes
✅ **No Server Management:** Fully managed services
✅ **High Availability:** Multi-AZ RDS, Lambda across AZs
✅ **Security:** VPC isolation, encryption, least privilege IAM
✅ **Observability:** CloudWatch logs, metrics, alarms
✅ **Fast Deployment:** CDK infrastructure in minutes

**Ready to implement?** Let me know and I'll create the CDK code!
