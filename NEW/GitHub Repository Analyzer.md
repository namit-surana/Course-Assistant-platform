# GitHub Repository Analyzer

This project currently includes:

- Phase 1: GitHub repository ingestion, filtering, documentation preview fetching, and `repo_context.json` generation
- Phase 2: CrewAI-based tree analysis that reads `repo_context.json` and produces a validated `tree_analysis_plan.json`

## Features

- FastAPI API with `POST /analyze` and `GET /health`
- Async GitHub API integration using `httpx.AsyncClient`
- Environment-based configuration with optional GitHub token support
- Deterministic path filtering
- Documentation file content fetch for selected doc-like files
- CrewAI-powered Phase 2 tree analysis with 2 sequential tasks
- Stable `repo_context.json` artifact generation
- Stable `tree_analysis_plan.json` artifact generation
- Local pytest coverage for filtering, Phase 2 loading, validation, prompt contract, and service output

## Project Structure

```text
src/
  app.py
  config/
    settings.py
  github_agent/          # GitHub Agent: phased ingestion + CrewAI analysis
    phase1/
      models/
        schemas.py
      services/
        github_service.py
        filter_service.py
        context_builder.py
    phase2/
      models/
        schemas.py
      services/
        loader.py
        preview_selector.py
        tree_analysis_service.py
      crew/
        config/
          agents.yaml
          tasks.yaml
        tree_analysis_crew.py
    phase3/
      models/
        schemas.py
      services/
        repository_analysis_service.py
      crew/
        config/
          agents.yaml
          tasks.yaml
        repository_analysis_crew.py
  api_ui/                 # FastAPI helpers: runs, SSE, audit (not the Next.js app)
  utils/
    logging.py
  tests/
    phase1/
    phase2/
    phase3/
    api_ui/
```

## Installation

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and adjust values as needed.

```env
GITHUB_TOKEN=
GEMINI_API_KEY=
CREWAI_TRACING_ENABLED=true
TREE_ANALYSIS_MODEL=gemini/gemini-2.5-flash
GITHUB_API_BASE_URL=https://api.github.com
REQUEST_TIMEOUT_SECONDS=20
MAX_FILE_SIZE_BYTES=200000
LOG_LEVEL=INFO
OUTPUT_DIR=outputs
```

`GITHUB_TOKEN` is optional for public repositories but strongly recommended to reduce rate-limit risk.
`GEMINI_API_KEY` is required when running the CrewAI-based Phase 2 tree analysis with Gemini.
`CREWAI_TRACING_ENABLED=true` enables CrewAI tracing. The Phase 2 runner also sets `tracing=True` explicitly on the Crew.
`TREE_ANALYSIS_MODEL` controls which model the Phase 2 Tree Analysis Agent uses. The default is `gemini/gemini-2.5-flash`.

## Phase 1

Phase 1 is a production-oriented FastAPI service that ingests a public GitHub repository, validates the URL, resolves the target branch, fetches repository metadata and the full recursive tree, removes obvious noise, fetches documentation file contents, and writes a `repo_context.json` artifact for later analysis phases.

## Run Locally

```bash
python -m uvicorn src.app:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Run With Docker

Build and run with plain Docker:

```bash
docker build -t repo-analyzer-phase1 .
docker run --rm -p 8000:8000 --env-file .env -v ${PWD}/outputs:/app/outputs repo-analyzer-phase1
```

Or use Docker Compose:

```bash
docker compose up --build
```

The service will be available at `http://127.0.0.1:8000`.

## API Usage

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Analyze a Repository

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\":\"https://github.com/octocat/Hello-World\"}"
```

Optional branch override:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main"
}
```

### Example Success Response

```json
{
  "status": "success",
  "repo_url": "https://github.com/owner/repo",
  "owner": "owner",
  "repo": "repo",
  "branch": "main",
  "repo_metadata": {
    "full_name": "owner/repo",
    "description": "Example repo",
    "default_branch": "main",
    "language": "Python",
    "size": "1.21 MB",
    "stargazers_count": 10,
    "forks_count": 2,
    "open_issues_count": 1,
    "fork": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-10T00:00:00Z",
    "pushed_at": "2024-01-11T00:00:00Z"
  },
  "tree_summary": {
    "total_items": 842,
    "total_blobs": 700,
    "total_trees": 142,
    "filtered_out_count": 511,
    "selected_file_count": 189
  },
  "selected_files": [
    "README.md",
    "package.json",
    "src/main.ts"
  ],
  "filtered_out_files": [
    "node_modules/react/index.js",
    "dist/app.bundle.js"
  ],
  "documentation_files": [
    {
      "path": "README.md",
      "size": 1024,
      "content": "# Example repo\n\nThis project demonstrates..."
    }
  ],
  "output_file": "outputs/owner__repo__repo_context.json"
}
```

### Error Handling

The service returns descriptive JSON errors for:

- invalid GitHub URLs
- repository not found
- branch not found
- GitHub rate limits
- request timeouts
- malformed GitHub responses
- empty repository trees

## Filtering

Phase 1 applies deterministic exclusion rules only.

- Excludes obvious noise such as `node_modules`, build artifacts, cache directories, common binary/media extensions, source maps, and oversized files.
- Keeps every remaining file.
- Fetches contents for selected documentation files such as `README*`, files under `docs/`, and common text documentation extensions.

The filtering logic is implemented in `src/github_agent/phase1/services/filter_service.py`.

## Artifact Output

Each successful analysis writes:

```text
{OUTPUT_DIR}/{owner}__{repo}__repo_context.json
```

Example structure:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "owner": "owner",
  "repo": "repo",
  "branch": "main",
  "repo_metadata": {
    "full_name": "owner/repo",
    "description": "Example repository",
    "default_branch": "main",
    "language": "Python",
    "stargazers_count": 0,
    "forks_count": 0,
    "open_issues_count": 0
  },
  "tree_summary": {
    "total_items": 0,
    "total_blobs": 0,
    "total_trees": 0,
    "filtered_out_count": 0,
    "selected_file_count": 0
  },
  "selected_files": [],
  "filtered_out_files": [],
  "documentation_files": [],
  "created_at": "2026-03-17T00:00:00+00:00"
}
```

## Phase 2

Phase 2 builds on the saved Phase 1 artifact. It does not replace Phase 1 and does not change the Phase 1 API.

Phase 2 does this:

- loads `repo_context.json`
- prepares a compact input payload for CrewAI
- runs Task 1 to group selected files into fixed repository components
- identifies `uncertain_files` and `unclassified_files`
- fetches limited previews only for Task 1 uncertain files
- runs Task 2 to resolve uncertainty using Task 1 context plus bounded previews
- infers repository type and entrypoint candidates
- validates the output against a strict Pydantic schema
- writes `tree_analysis_plan.json`

Phase 2 does not do:

- deep code review
- security review
- final report generation
- multi-agent orchestration
- full-file content fetching for the whole repository

### Fixed Phase 2 Components

Phase 2 classifies files into a fixed taxonomy:

- `overview_docs`
- `frontend`
- `backend`
- `database_schema`
- `workers`
- `integrations`
- `config_env`
- `build_dependencies`
- `infra_deployment`
- `tests`
- `tools_scripts`
- `data_assets_dataset`

Files are assigned by best-fit primary responsibility, not just folder name.

### Run Phase 2

Use the service entry point from Python:

```python
import asyncio

from src.github_agent.phase2.services.tree_analysis_service import create_tree_analysis_service

service = create_tree_analysis_service()
plan = asyncio.run(service.run_phase2_from_file("outputs/owner__repo__repo_context.json"))
print(plan.model_dump())
```

Output file convention:

```text
outputs/{owner}__{repo}__tree_analysis_plan.json
```

### Example Tree Analysis Output

```json
{
  "repo_url": "https://github.com/owner/repo",
  "owner": "owner",
  "repo": "repo",
  "branch": "main",
  "source_repo_context_file": "outputs/owner__repo__repo_context.json",
  "analysis_input": {
    "repo_url": "https://github.com/owner/repo",
    "owner": "owner",
    "repo": "repo",
    "branch": "main",
    "repo_metadata": {
      "full_name": "owner/repo",
      "description": "Example repo",
      "default_branch": "main",
      "language": "Python",
      "size": "1.21 MB",
      "stargazers_count": 10,
      "forks_count": 2,
      "open_issues_count": 1,
      "fork": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-10T00:00:00Z",
      "pushed_at": "2024-01-11T00:00:00Z"
    },
    "tree_summary": {
      "total_items": 842,
      "total_blobs": 700,
      "total_trees": 142,
      "filtered_out_count": 511,
      "selected_file_count": 189
    },
    "selected_files": [
      "README.md",
      "requirements.txt",
      "src/main.py",
      "frontend/package.json"
    ],
    "documentation_previews": [
      {
        "path": "README.md",
        "size": 1024,
        "content": "# Example repo"
      }
    ],
    "guaranteed_coverage_metadata": null
  },
  "task1_output": {
    "repo_type": "full_stack_app",
    "groups": {
      "overview_docs": ["README.md"],
      "build_dependencies": ["requirements.txt", "frontend/package.json"],
      "backend": ["src/main.py"]
    },
    "uncertain_files": [
      {
        "path": "src/services/s3_service.py",
        "candidate_groups": ["integrations", "backend"],
        "reason": "Service name suggests external integration but exact role is unclear from the path alone."
      }
    ],
    "unclassified_files": [],
    "unknowns": []
  },
  "task2_input": {
    "repo_url": "https://github.com/owner/repo",
    "owner": "owner",
    "repo": "repo",
    "branch": "main",
    "uncertain_files": [
      {
        "path": "src/services/s3_service.py",
        "candidate_groups": ["integrations", "backend"],
        "reason": "Service name suggests external integration but exact role is unclear from the path alone."
      }
    ],
    "fetched_previews": [
      {
        "path": "src/services/s3_service.py",
        "preview": "class S3Service: ..."
      }
    ]
  },
  "task2_output": {
    "resolved_groups": {
      "integrations": ["src/services/s3_service.py"]
    },
    "remaining_uncertain_files": [],
    "unknowns": []
  },
  "plan": {
    "repo_type": "full_stack_app",
    "confidence": 0.91,
    "important_paths": [
      "README.md",
      "requirements.txt",
      "src/main.py",
      "frontend/package.json",
      "src/services/s3_service.py"
    ],
    "entrypoint_candidates": {
      "backend": ["src/main.py"],
      "frontend": []
    },
    "groups": {
      "overview_docs": ["README.md"],
      "build_dependencies": ["requirements.txt", "frontend/package.json"],
      "backend": ["src/main.py"],
      "integrations": ["src/services/s3_service.py"]
    },
    "fetch_priority": [
      "README.md",
      "requirements.txt",
      "src/main.py",
      "frontend/package.json",
      "src/services/s3_service.py"
    ],
    "remaining_uncertain_files": [],
    "unclassified_files": [],
    "unknowns": [
      "Frontend entrypoint is unclear from selected files"
    ]
  },
  "created_at": "2026-03-17T00:00:00+00:00"
}
```

## Test

Run the test suite with:

```bash
pytest src/tests -q
```

The tests are local and do not depend on live GitHub or live LLM access. CrewAI execution is mocked in Phase 2 unit tests.
