# Local Full-Stack Testing

This runs the local version of the AWS Phase 2 stack:

- PostgreSQL in Docker for metadata and feedback
- LocalStack in Docker for S3 and SQS
- FastAPI API in Docker
- Worker in Docker
- Next.js frontend on the host machine

## 1. Create `.env`

From the repository root:

```bash
cp .env.example .env
```

For local Docker testing, use values like:

```env
SECRET_KEY=dev-secret
DATABASE_URL=postgresql+psycopg://coursework:coursework@db:5432/coursework

AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localstack:4566
AWS_PUBLIC_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

S3_BUCKET_NAME=prod-bucket-uploads
SQS_QUEUE_URL=http://localstack:4566/000000000000/prod-queue-analysis

FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173

GEMINI_API_KEY=your_gemini_key
GITHUB_TOKEN=

SES_SENDER_EMAIL=
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=

WORKER_POLL_WAIT_SECONDS=20
WORKER_IDLE_SLEEP_SECONDS=2
WORKER_MAX_MESSAGES=5
WORKER_ENABLE_PPT_ANALYSIS=true
WORKER_ENABLE_REPOSITORY_ANALYSIS=true

CREWAI_TRACING_ENABLED=true
TREE_ANALYSIS_MODEL=gemini/gemini-2.5-flash
REPOSITORY_ANALYSIS_MODEL=gemini/gemini-2.5-flash
GITHUB_API_BASE_URL=https://api.github.com
REQUEST_TIMEOUT_SECONDS=20
MAX_FILE_SIZE_BYTES=200000
LOG_LEVEL=INFO
OUTPUT_DIR=outputs
```

Do not paste real `.env` output in group chat. It may include API keys.

## 2. Start Backend Services

Terminal 1:

```bash
docker compose down
docker compose up --build db localstack api worker
```

Leave this terminal running.

LocalStack automatically creates:

- `s3://prod-bucket-uploads`
- `prod-queue-analysis`

Look for:

```text
LocalStack resources ready: s3://prod-bucket-uploads, queue=prod-queue-analysis
```

## 3. Run Migrations

Terminal 2:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic current
```

Expected current migration:

```text
20260501_0002
```

## 4. Verify Local AWS Resources

```bash
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4566 sqs list-queues
```

```bash
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4566 s3 ls
```

## 5. Start Frontend

Still in Terminal 2, or in another terminal:

```bash
cd Frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## 6. Manual End-to-End Test

1. Open `/home`.
2. Create an event.
3. Refresh the page.
4. Confirm the event is still visible.
5. Open the event.
6. Add a team submission.
7. Upload a `.pptx` or `.pdf` if desired.
8. Submit.
9. Refresh the page.
10. Confirm the submission reloads from the database.

## 7. Database Checks

Open Postgres:

```bash
docker compose exec db psql -U coursework -d coursework
```

Useful SQL:

```sql
select id, name, type, status, submission_deadline
from evaluation_events
order by created_at desc;
```

```sql
select id, title, event_id
from assignments
order by created_at desc;
```

```sql
select category, max_score
from rubric_criteria
order by created_at desc;
```

```sql
select id, event_id, team_name, repo_url, status
from submissions
order by created_at desc;
```

```sql
select id, submission_id, status, sqs_message_id, error_message
from analysis_jobs
order by created_at desc;
```

Exit:

```sql
\q
```

## 8. Logs

```bash
docker compose logs -f api
```

```bash
docker compose logs -f worker
```

```bash
docker compose logs -f localstack
```

