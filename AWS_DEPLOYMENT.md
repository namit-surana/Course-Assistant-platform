# AWS Deployment (what’s done + what’s left)

This file answers only two questions:
- **What’s completed (and how)?**
- **What’s remaining (and how do we do it)?**

---

## Completed (S3 + SQS) — what it means + how it works

### ✅ S3 (artifact storage)
**What is completed**
- A private S3 bucket exists (your uploads bucket).
- IAM permissions allow the backend/worker to access it.
- Bucket CORS allows browser uploads (for presigned PUTs) from your frontend origin.

**How it works in this app**
- API generates a **presigned URL** → browser uploads PPT/video directly to S3.
- API stores the S3 `object_key` in Postgres as part of the submission artifacts.
- Worker later downloads those objects from S3 to analyze them.

### ✅ SQS (job queue)
**What is completed**
- An SQS queue exists (your analysis queue).
- IAM permissions allow API to `SendMessage`, and worker to `ReceiveMessage/DeleteMessage`.

**How it works in this app**
- Teacher clicks **Start processing** → API creates an `analysis_job` row + sends **1 message** to SQS.
- Worker polls SQS, processes the job, writes results back to Postgres.

---

## Remaining — what you must deploy on AWS to run in the cloud

### 1) RDS PostgreSQL (database) — **required**
**Goal**: API + worker use a managed Postgres instead of local Docker DB.

**Do this**
- Create **RDS PostgreSQL** in the same region as S3/SQS (e.g. `us-east-1`).
- Put it in a VPC/subnets, with a security group that allows:
  - inbound `5432` **only** from the ECS tasks (API + worker)
- Save the connection string as `DATABASE_URL`.

**Then**
- Run migrations against RDS:

```bash
alembic upgrade head
```

### 2) ECR (container registry) — **required**
**Goal**: store Docker images for API + worker.

**Do this**
- Create 2 ECR repos:
  - `course-assistant-api`
  - `course-assistant-worker`
- Push images:

```bash
aws ecr get-login-password --region <region> `
  | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

docker build -t course-assistant-api .
docker build -f Dockerfile.worker -t course-assistant-worker .

docker tag course-assistant-api:latest <account>.dkr.ecr.<region>.amazonaws.com/course-assistant-api:latest
docker tag course-assistant-worker:latest <account>.dkr.ecr.<region>.amazonaws.com/course-assistant-worker:latest

docker push <account>.dkr.ecr.<region>.amazonaws.com/course-assistant-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/course-assistant-worker:latest
```

### 3) ECS Fargate (run API + worker) — **required**
**Goal**: run both services continuously in the cloud.

**Do this**
- Create an **ECS cluster**.
- Create **2 ECS services**:
  - **API service** (FastAPI) using the API image
  - **Worker service** using the worker image

**IAM (best practice)**
- Use **task roles** (no hardcoded AWS keys in env):
  - API task role: S3 (presign/read), SQS (send), SecretsManager (read)
  - Worker task role: SQS (receive/delete), S3 (get), SecretsManager (read)

**Env vars (store in Secrets Manager)**
- `DATABASE_URL`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `SQS_QUEUE_URL`
- `GEMINI_API_KEY`
- `GITHUB_TOKEN`

### 4) ALB (public API endpoint) — **required**
**Goal**: expose the API to the internet securely.

**Do this**
- Create an **Application Load Balancer** → Target Group → point to the API service.
- Health check path: `/health`
- Result: you get an ALB URL like `http(s)://<alb-dns-name>`

### 5) Frontend hosting (Vercel or Amplify) — **required**
**Goal**: users can access the UI from the internet.

**Do this**
- Deploy Next.js frontend on:
  - Vercel (fastest), OR
  - Amplify Hosting (AWS-only)
- Set:
  - `NEXT_PUBLIC_API_BASE_URL=<your ALB URL>`

---

## Final smoke check (cloud)

- Open frontend → create event → submit artifacts → click **Start processing**
- Confirm:
  - SQS receives a message
  - Worker consumes it and finishes
  - Submission becomes `completed`
  - Results show in the UI

