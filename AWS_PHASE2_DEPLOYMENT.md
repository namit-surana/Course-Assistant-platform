# AWS Phase 2 Deployment Guide

Phase 2 creates the data and storage resources that the API and worker need:

- RDS PostgreSQL
- S3 uploads bucket
- SQS analysis queue
- Secrets Manager secret
- CloudWatch log groups

Redis is skipped for now because the codebase does not use Redis.

## Resource Names

Recommended names:

```text
S3 uploads bucket: prod-bucket-uploads-<unique-suffix>
SQS queue: prod-queue-analysis
RDS instance: prod-db-postgres
Database name: coursework
Secrets Manager secret: prod-secrets-app
CloudWatch API log group: prod-logs-api
CloudWatch worker log group: prod-logs-worker
```

S3 bucket names are globally unique. Add your initials, team name, or AWS account id suffix.

## 1. Create S3 Uploads Bucket

Service: **S3**

Settings:

- Block public access: ON
- Encryption: ON
- Versioning: optional
- CORS: required for browser uploads

Example CORS:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "POST", "GET"],
    "AllowedOrigins": [
      "http://localhost:3000",
      "https://your-frontend-domain.com"
    ],
    "ExposeHeaders": ["ETag"]
  }
]
```

CLI example:

```bash
aws s3api create-bucket \
  --bucket prod-bucket-uploads-<unique-suffix> \
  --region us-east-1
```

```bash
aws s3api put-public-access-block \
  --bucket prod-bucket-uploads-<unique-suffix> \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

```bash
aws s3api put-bucket-encryption \
  --bucket prod-bucket-uploads-<unique-suffix> \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

Save the final bucket name as `S3_BUCKET_NAME`.

## 2. Create SQS Queue

Service: **SQS**

Settings:

- Type: Standard
- Visibility timeout: 15 to 30 minutes
- Message retention: 4 days or more

CLI example:

```bash
aws sqs create-queue \
  --queue-name prod-queue-analysis \
  --attributes VisibilityTimeout=1800,MessageRetentionPeriod=345600
```

Get the queue URL:

```bash
aws sqs get-queue-url --queue-name prod-queue-analysis
```

Save it as `SQS_QUEUE_URL`.

## 3. Create RDS PostgreSQL

Service: **RDS**

Settings:

- Engine: PostgreSQL
- DB instance identifier: `prod-db-postgres`
- Database name: `coursework`
- Public access: No
- Subnet group: private data subnets
- Security group: `prod-sg-rds`
- Inbound PostgreSQL `5432`: allow only `prod-sg-api` and `prod-sg-worker`

Recommended student-project settings:

- Single-AZ is acceptable for lower cost
- Small instance class is acceptable
- Enable deletion protection only if you do not want easy cleanup

After creation, build:

```env
DATABASE_URL=postgresql+psycopg://<username>:<password>@<rds-endpoint>:5432/coursework
```

## 4. Create Secrets Manager Secret

Service: **Secrets Manager**

Secret name:

```text
prod-secrets-app
```

Secret JSON:

```json
{
  "DATABASE_URL": "postgresql+psycopg://<username>:<password>@<rds-endpoint>:5432/coursework",
  "SECRET_KEY": "<strong-random-secret>",
  "GEMINI_API_KEY": "<gemini-key>",
  "GITHUB_TOKEN": "",
  "AWS_REGION": "us-east-1",
  "S3_BUCKET_NAME": "prod-bucket-uploads-<unique-suffix>",
  "SQS_QUEUE_URL": "<queue-url>",
  "FRONTEND_URL": "https://your-frontend-domain.com",
  "CORS_ALLOWED_ORIGINS": "https://your-frontend-domain.com",
  "SES_SENDER_EMAIL": "",
  "COGNITO_USER_POOL_ID": "",
  "COGNITO_CLIENT_ID": "",
  "WORKER_ENABLE_PPT_ANALYSIS": "true",
  "WORKER_ENABLE_REPOSITORY_ANALYSIS": "true"
}
```

Do not set `AWS_ENDPOINT_URL` or `AWS_PUBLIC_ENDPOINT_URL` in production. Those are only for LocalStack.

## 5. Create CloudWatch Log Groups

Service: **CloudWatch Logs**

Create:

```bash
aws logs create-log-group --log-group-name prod-logs-api
aws logs create-log-group --log-group-name prod-logs-worker
```

Set retention:

```bash
aws logs put-retention-policy --log-group-name prod-logs-api --retention-in-days 14
aws logs put-retention-policy --log-group-name prod-logs-worker --retention-in-days 14
```

## 6. Apply Database Migrations

Because RDS is private, do not expect your laptop to connect directly.

Recommended path:

1. Build and push the API image in Phase 3.
2. Create an ECS one-off task in the private API subnets.
3. Run:

```bash
alembic upgrade head
```

The task needs the same `DATABASE_URL` secret as the API.

For local verification only:

```bash
docker compose exec api alembic upgrade head
```

## 7. How Code Deployment Fits In

Phase 2 creates resources. The code is actually deployed in later phases:

- Phase 3: ECR repositories
- Phase 4: ECS cluster, task definitions, API service, worker service
- Phase 5: ALB and target group

You can still create Phase 2 now. The deployed API/worker will use these resources after ECS is set up.

## 8. Update and Rollback Notes

Code updates:

```bash
docker build -t coursework-api .
docker build -f Dockerfile.worker -t coursework-worker .
docker push <ecr-api-image>
docker push <ecr-worker-image>
aws ecs update-service --cluster prod-cluster --service prod-service-api --force-new-deployment
aws ecs update-service --cluster prod-cluster --service prod-service-worker --force-new-deployment
```

Schema updates:

- Do not edit old migrations after they are applied.
- Add a new Alembic migration.
- Run `alembic upgrade head`.

Rollback:

- ECS code rollback is easy: redeploy an older image tag.
- Database rollback is harder: avoid destructive migrations and keep backups/snapshots.

## 9. Final Phase 2 Checklist

- [ ] S3 bucket exists
- [ ] S3 CORS configured
- [ ] SQS queue exists
- [ ] RDS PostgreSQL exists in private data subnets
- [ ] RDS security group allows API and worker SGs
- [ ] Secrets Manager secret exists
- [ ] CloudWatch log groups exist
- [ ] Secret values match env vars in `.env.example`
- [ ] Alembic migration plan is ready for ECS one-off task

