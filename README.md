# CourseWork Eval Platform

An AI-powered academic project evaluation platform where student teams submit their PPT, demo video, and GitHub repo — and receive detailed, rubric-based feedback automatically.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [How the AI Analysis Works](#how-the-ai-analysis-works)
- [Roles & Permissions](#roles--permissions)
- [Team & Task Division](#team--task-division)
- [Deployment (AWS)](#deployment-aws)

---

## Overview

| Actor | What they do |
|---|---|
| **Professor** | Creates courses, invites students, builds rubrics per assignment |
| **TA** | Views all team feedback, can override AI scores |
| **Student** | Joins a course, forms a team, submits PPT + video + GitHub repo |

**Submission flow:**

```
Student submits → files upload to S3 → job queued in SQS
→ Worker picks up job → analyzes PPT, video, GitHub via Gemini
→ Scores written to DB → email sent → feedback visible on dashboard
```

---

## Architecture

```
Users (Professor / TA / Student)
        │
        ▼
  CloudFront CDN + Route 53
        │
        ▼
  Application Load Balancer
        │
   ┌────▼────────────────────────────────────────┐
   │                  AWS VPC                     │
   │                                              │
   │   ┌──────────────────────────────────────┐  │
   │   │  FastAPI API Server (ECS Fargate)     │  │
   │   └──────┬──────────┬────────────┬───────┘  │
   │          │          │            │           │
   │        RDS       ElastiCache    SQS          │
   │      (PostgreSQL)  (Redis)       │           │
   │                                 │           │
   │   ┌─────────────────────────────▼────────┐  │
   │   │  Analysis Worker Server (ECS Fargate) │  │
   │   │  PPT Analyzer │ Video │ GitHub        │  │
   │   └──────────────────────────────────────┘  │
   │                                              │
   └──────────────────────────────────────────────┘
          │              │              │
         S3            SES          Cognito
   (File Storage)   (Emails)        (Auth)

External: Google Gemini API · GitHub API
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS + React Query |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 (RDS) |
| Auth | AWS Cognito — Google OAuth (students/TAs) + Email/Password (professors) |
| File Storage | AWS S3 + CloudFront |
| Job Queue | AWS SQS |
| Email | AWS SES |
| AI — Video & Text | Google Gemini 1.5 Pro |
| AI — PPT Parsing | `python-pptx` + Gemini |
| AI — GitHub | PyGithub + Gemini |
| Containers | Docker + ECS Fargate |
| Local AWS | LocalStack |
| Migrations | Alembic |

---

## Project Structure

Layout of **this repository** (FastAPI + CrewAI analyzer + Next.js UI):

```
.
├── .dockerignore
├── .gitignore
├── docker-compose.yml            # api service; mounts ./outputs → /app/outputs
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
├── outputs/                      # Created at runtime: repo_context, analysis JSON, reports (see OUTPUT_DIR)
│
├── Frontend/                     # Next.js app (dashboard, repo analyze UI, events)
│   ├── app/                      # App Router pages
│   ├── components/
│   └── lib/                      # Types, stores, API helpers
│
└── src/                          # Python package root (run as: uvicorn src.app:app)
    ├── __init__.py
    ├── app.py                    # FastAPI app, routes (/health, /api/v1/*, …)
    ├── config/
    │   ├── __init__.py
    │   └── settings.py           # Pydantic settings / env
    │
    ├── github_agent/             # GitHub repo pipeline (ingest → tree plan → deep analysis)
    │   ├── __init__.py
    │   ├── phase1/               # GitHub API, filter tree, repo_context.json
    │   │   ├── models/
    │   │   └── services/
    │   ├── phase2/               # CrewAI tree analysis → tree_analysis_plan.json
    │   │   ├── models/
    │   │   ├── services/
    │   │   └── crew/
    │   │       └── config/       # agents.yaml, tasks.yaml
    │   └── phase3/               # CrewAI repository analysis + markdown report
    │       ├── models/
    │       ├── services/
    │       ├── flows/
    │       └── crew/
    │           └── config/
    │
    ├── api_ui/                   # Backend support for run state/progress + audit logging
    │   ├── __init__.py
    │   ├── models/
    │   └── services/             # analysis_run_service, run_store, crewai_live_events, audit_log
    │
    ├── ppt_agent/                # PPT-side analysis (python-pptx / Gemini integration)
    │   ├── __init__.py
    │   └── ppt_analyzer.py
    │
    ├── utils/                    # Logging, usage metrics
    │
    └── tests/                    # pytest
        ├── conftest.py
        ├── phase1/
        ├── phase2/
        ├── phase3/
        └── api_ui/
```

*Target production layout (separate `backend/` API, Vite `frontend/`, workers, Terraform) is described in [Architecture](#architecture); it is not the folder layout above.*

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Node.js 20+](https://nodejs.org/)
- [Python 3.11+](https://www.python.org/)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd coursework-eval

cp .env.example .env
# Fill in your GEMINI_API_KEY and other values in .env
```

### 2. Start the full stack

```bash
docker compose -f docker-compose.aws.yml up --build
```

This starts:
| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL | localhost:5432 |

### 3. Run database migrations

```bash
# In a separate terminal (after containers are up)
docker compose exec api alembic upgrade head
```

### 4. Install frontend deps (for local non-Docker dev)

```bash
cd Frontend
npm install
npm run dev
```

### 5. Run backend locally (without Docker)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret |
| `DATABASE_URL` | PostgreSQL connection string |
| `AWS_REGION` | e.g. `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `S3_BUCKET_NAME` | S3 bucket for PPT + video uploads |
| `SQS_QUEUE_URL` | Fallback SQS queue URL for analysis jobs |
| `SQS_QUEUE_URL_GIT` | Dedicated SQS queue URL for `git_analysis` jobs |
| `SQS_QUEUE_URL_PPT` | Dedicated SQS queue URL for `ppt_analysis` jobs |
| `SQS_QUEUE_URL_VIDEO` | Dedicated SQS queue URL for `video_analysis` jobs |
| `SQS_QUEUE_URL_FINAL_GRADING` | Dedicated SQS queue URL for `final_grading_analysis` jobs |
| `WORKER_JOB_TYPE` | Optional worker mode (`git_analysis`, `ppt_analysis`, `video_analysis`, `final_grading_analysis`) |
| `FINAL_GRADING_MODEL` | LLM model used by the final grading CrewAI agent |
| `SES_SENDER_EMAIL` | Verified email address in SES |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID |
| `COGNITO_CLIENT_ID` | Cognito App Client ID |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GITHUB_TOKEN` | GitHub PAT (optional, for private repos) |
| `FRONTEND_URL` | Frontend URL for CORS (e.g. `http://localhost:5173`) |

> For local development, Docker Compose automatically sets `AWS_ACCESS_KEY_ID=test` and points AWS SDK to LocalStack.

---

## API Reference

Interactive docs available at **http://localhost:8000/api/docs** (Swagger UI).

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Professor registration (email + password) |
| `POST` | `/api/auth/login` | Professor login → JWT |
| `GET` | `/api/auth/google/callback` | Google OAuth callback → JWT |
| `GET` | `/api/auth/me` | Get current user |

### Courses
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/courses` | Create course (professor) |
| `GET` | `/api/courses` | List my courses |
| `POST` | `/api/courses/{id}/join` | Join via invite code |
| `GET` | `/api/courses/{id}/members` | List members |

### Assignments & Rubric
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/assignments/courses/{id}/assignments` | Create assignment |
| `POST` | `/api/assignments/{id}/rubric` | Add rubric criterion |
| `GET` | `/api/assignments/{id}/results` | All team scores |
| `GET` | `/api/assignments/{id}/export` | CSV export |

### Submissions
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/submissions/presigned-url` | Get S3 upload URL |
| `POST` | `/api/submissions` | Submit (after S3 upload) |
| `GET` | `/api/submissions/{id}` | Get status + feedback |

### Feedback
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/feedback/{submission_id}` | Full feedback with scores |
| `PATCH` | `/api/feedback/scores/{score_id}` | Override score (TA/Professor) |

---

## How the AI Analysis Works

When a team submits, three analyzers run in parallel inside the worker:

### 1. PPT Analyzer
- Downloads PPT from S3
- Extracts all slide text using `python-pptx`
- Sends slide content + rubric to **Gemini 1.5 Pro**
- Returns a score and explanation per rubric criterion

### 2. Video Analyzer
- Downloads video from S3
- Uploads to **Gemini Files API** (supports native video understanding)
- Gemini watches the video — analyzes both speech and visual content
- Returns scores based on what was demonstrated

### 3. GitHub Analyzer
- Fetches repo metadata via GitHub API: README, file tree, languages, commit count
- Sends to **Gemini 1.5 Pro** with rubric
- Evaluates code quality, project structure, documentation

### Score Aggregation
- Scores from all 3 analyzers are mapped to rubric criteria
- Final `total_score` = sum of all criterion scores
- `overall_comment` = combined narrative summary
- Stored in DB → visible on feedback dashboard

### Override Flow
```
AI generates score
    → TA or Professor can override any individual score
    → Original score + override reason saved in feedback_overrides table
    → Final displayed score = override (if exists) else AI score
```

---

## Roles & Permissions

| Action | Professor | TA | Student |
|---|---|---|---|
| Create course | ✅ | ❌ | ❌ |
| Invite students | ✅ | ❌ | ❌ |
| Create assignment | ✅ | ❌ | ❌ |
| Define rubric | ✅ | ❌ | ❌ |
| Submit project | ❌ | ❌ | ✅ |
| View own feedback | ❌ | ❌ | ✅ |
| View all teams' feedback | ✅ | ✅ | ❌ |
| Override AI scores | ✅ | ✅ | ❌ |
| Export results CSV | ✅ | ✅ | ❌ |

---

## Team & Task Division

The project is split into 3 parallel workstreams — each member owns a full vertical slice with minimal overlap.

---

### Member 1 — Backend & Auth
> Owns: `backend/app/routers/`, `backend/app/services/`, `backend/app/models/`, `backend/alembic/`

| Task | Files |
|---|---|
| AWS Cognito setup (Google OAuth + email/password) | `routers/auth.py`, `services/auth_service.py` |
| JWT middleware + role-based dependencies | `app/dependencies.py` |
| Courses API (create, join, members) | `routers/courses.py` |
| Teams API (create, join) | `routers/teams.py` |
| Assignments API + rubric CRUD | `routers/assignments.py` |
| Submissions API + S3 presigned URLs | `routers/submissions.py`, `services/s3_service.py` |
| Alembic DB migrations | `alembic/versions/` |
| SQS publish on submit | `services/sqs_service.py` |

**Skills:** Python, FastAPI, PostgreSQL, AWS (Cognito, S3, SQS)

---

### Member 2 — AI Workers & Analysis Pipeline
> Owns: `backend/app/worker/`, `backend/app/routers/feedback.py`, `backend/app/services/email_service.py`

| Task | Files |
|---|---|
| PPT analyzer (python-pptx + Gemini) | `worker/analyzers/ppt_analyzer.py` |
| Video analyzer (Gemini Files API) | `worker/analyzers/video_analyzer.py` |
| GitHub analyzer (PyGithub + Gemini) | `worker/analyzers/github_analyzer.py` |
| Gemini prompt engineering for rubric scoring | All analyzers |
| JSON response parsing + score aggregation | `worker/processor.py` |
| Write feedback to DB + update submission status | `worker/main.py` |
| SES email notification on completion | `services/email_service.py` |
| Feedback override API | `routers/feedback.py` |

**Skills:** Python, LLM APIs (Gemini), AWS (SQS, SES, S3)

---

### Member 3 — Frontend
> Owns: `frontend/src/`

| Task | Files |
|---|---|
| Login page (Google OAuth + email/password) | `pages/LoginPage.jsx` |
| Dashboard (role-aware: Professor / TA / Student) | `pages/DashboardPage.jsx` |
| Course page + invite code join flow | `pages/CoursePage.jsx` |
| Assignment page + rubric builder (Professor view) | `pages/AssignmentPage.jsx` |
| Submit page (drag-drop PPT, video, GitHub URL) | `pages/SubmitPage.jsx` |
| Feedback page (radar chart, per-criterion scores) | `pages/FeedbackPage.jsx` |
| Shared UI components (navbar, cards, badges) | `components/` |
| API hooks + Axios service | `hooks/`, `services/api.js` |

**Skills:** React 18, Tailwind CSS, React Query, Recharts

---

### How the Three Pieces Connect

```
Member 1 (Backend API)  ──defines API contracts──►  Member 3 (Frontend)
Member 1 (Backend API)  ──publishes SQS job──────►  Member 2 (Worker)
Member 2 (Worker)       ──writes feedback to DB──►  Member 1 owns DB schema
```

> **Rule:** Member 1 defines DB models and migrations first — Members 2 and 3 depend on the schema being stable before writing to it or querying it.

---

### Week-by-Week Timeline

| Week | Member 1 — Backend | Member 2 — Workers | Member 3 — Frontend |
|---|---|---|---|
| **1** | Cognito auth + JWT + DB migrations | Gemini API setup + PPT analyzer | Login page + routing + API service |
| **2** | Courses, Teams, Assignments APIs | Video analyzer + GitHub analyzer | Dashboard + Course page |
| **3** | Submissions API + S3 presigned URLs | Score aggregation + DB writes + SES email | Submit page + Feedback page |
| **4** | Feedback override API + CSV export | Worker testing + prompt tuning | Polish UI + radar chart + override UI |
| **5** | Docker + ECS deployment | Worker Dockerfile + scaling config | Frontend build + CloudFront deploy |

---

### Quick Start Per Member

**Member 1 & 2** (backend):
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
docker compose -f docker-compose.aws.yml up db
uvicorn app.main:app --reload
```

**Member 3** (frontend):
```bash
cd frontend
npm install
npm run dev    # proxies /api → localhost:8000
```

> Member 3 can use hardcoded mock data in hooks while Member 1 builds real endpoints, then swap to live API calls once routes are ready.

---

## Deployment (AWS)

For AWS Phase 2 data/storage deployment, see [AWS_PHASE2_DEPLOYMENT.md](AWS_PHASE2_DEPLOYMENT.md).

### Services used in production

| AWS Service | Purpose |
|---|---|
| ECS Fargate | API server + worker server (always-on containers) |
| RDS PostgreSQL | Primary database |
| ElastiCache Redis | Sessions and caching |
| S3 + CloudFront | File storage + CDN |
| SQS | Analysis job queue |
| SES | Email notifications |
| Cognito | Authentication (Google OAuth + email/password) |
| ECR | Docker image registry |
| ALB | Application Load Balancer |
| Route 53 | DNS |
| Secrets Manager | API keys and DB credentials |
| CloudWatch | Logs and monitoring |

### Deploy steps (summary)

```bash
# 1. Build and push Docker images to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-url>
docker build -t coursework-api ./backend
docker build -f ./backend/Dockerfile.worker -t coursework-worker ./backend
docker tag coursework-api <ecr-url>/coursework-api:latest
docker tag coursework-worker <ecr-url>/coursework-worker:latest
docker push <ecr-url>/coursework-api:latest
docker push <ecr-url>/coursework-worker:latest

# 2. Run migrations against RDS
DATABASE_URL=<rds-url> alembic upgrade head

# 3. Update ECS services
aws ecs update-service --cluster coursework --service api --force-new-deployment
aws ecs update-service --cluster coursework --service worker --force-new-deployment
```

> Full Terraform infrastructure-as-code is in `infrastructure/` (coming soon).

---

## Build Phases

- [x] Phase 1 — Project structure, DB models, config
- [x] Phase 2 — Auth (Cognito + JWT middleware)
- [x] Phase 3 — Core API routes (courses, teams, assignments)
- [x] Phase 4 — Submission flow (S3 presigned URLs + SQS)
- [x] Phase 5 — AI analysis workers (PPT + video + GitHub)
- [] Phase 6 — Frontend (login, dashboard, submit, feedback)
- [ ] Phase 7 — Deployment (ECS + RDS + Terraform)
