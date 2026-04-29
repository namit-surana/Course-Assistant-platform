import asyncio
import json
import logging
import tempfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from src.api_ui.models.schemas import AnalysisRunState
from src.api_ui.services.analysis_run_service import AnalysisRunService
from src.api_ui.services.audit_log_service import AuditLogService
from src.api_ui.services.run_store import AnalysisRunStore, RunNotFoundError
from src.config.settings import Settings, get_settings
from src.github_agent.phase1.models.schemas import AnalyzeRequest, AnalyzeResponse
from src.github_agent.phase1.services.context_builder import ContextBuilder
from src.github_agent.phase1.services.filter_service import FilterService
from src.github_agent.phase1.services.github_service import (
    BranchNotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
    GitHubTimeoutError,
    InvalidGitHubUrlError,
    MalformedGitHubResponseError,
    RepositoryNotFoundError,
)
from src.github_agent.phase2.services.tree_analysis_service import (
    TreeAnalysisParserError,
    TreeAnalysisService,
    create_tree_analysis_service,
)
from src.github_agent.phase3.services.repository_analysis_service import (
    RepositoryAnalysisParserError,
    RepositoryAnalysisService,
    create_repository_analysis_service,
)
from src.ppt_agent.ppt_analyzer import analyze_ppt
from src.utils.logging import configure_logging


logger = logging.getLogger(__name__)
RUN_STORE = AnalysisRunStore(
    audit_log_service=AuditLogService(get_settings().output_dir / "run_audit")
)
RUN_SERVICE = AnalysisRunService(RUN_STORE)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


app = FastAPI(title="GitHub Repository Analyzer", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_github_service(settings: Settings = Depends(get_settings)) -> GitHubService:
    return GitHubService(
        api_base_url=settings.github_api_base_url,
        request_timeout_seconds=settings.request_timeout_seconds,
        github_token=settings.github_token,
        cache_dir=settings.output_dir / "file_cache",
    )


def get_filter_service(settings: Settings = Depends(get_settings)) -> FilterService:
    return FilterService(max_file_size_bytes=settings.max_file_size_bytes)


def get_context_builder(settings: Settings = Depends(get_settings)) -> ContextBuilder:
    return ContextBuilder(output_dir=settings.output_dir)


def get_tree_analysis_service(
    settings: Settings = Depends(get_settings),
    github_service: GitHubService = Depends(get_github_service),
) -> TreeAnalysisService:
    return create_tree_analysis_service(
        settings,
        preview_fetcher=github_service.get_file_preview,
    )


def get_repository_analysis_service(
    settings: Settings = Depends(get_settings),
    github_service: GitHubService = Depends(get_github_service),
) -> RepositoryAnalysisService:
    return create_repository_analysis_service(
        settings,
        preview_fetcher=github_service.get_file_preview,
    )


def get_analysis_run_service() -> AnalysisRunService:
    return RUN_SERVICE


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def redirect_root_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.post("/api/runs", response_model=AnalysisRunState)
async def create_run(
    request: AnalyzeRequest,
    analysis_run_service: AnalysisRunService = Depends(get_analysis_run_service),
    github_service: GitHubService = Depends(get_github_service),
    filter_service: FilterService = Depends(get_filter_service),
    context_builder: ContextBuilder = Depends(get_context_builder),
    tree_analysis_service: TreeAnalysisService = Depends(get_tree_analysis_service),
    repository_analysis_service: RepositoryAnalysisService = Depends(
        get_repository_analysis_service
    ),
) -> AnalysisRunState:
    return await analysis_run_service.start_run(
        request,
        github_service=github_service,
        filter_service=filter_service,
        context_builder=context_builder,
        tree_analysis_service=tree_analysis_service,
        repository_analysis_service=repository_analysis_service,
    )


@app.get("/api/runs/{run_id}", response_model=AnalysisRunState)
async def get_run(
    run_id: str,
    analysis_run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> AnalysisRunState:
    try:
        return analysis_run_service.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Analysis run not found.") from exc


@app.get("/api/runs", response_model=list[AnalysisRunState])
async def list_runs(
    limit: int = 20,
    analysis_run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> list[AnalysisRunState]:
    bounded_limit = max(1, min(limit, 50))
    return analysis_run_service.store.list_runs(limit=bounded_limit)


@app.get("/api/runs/{run_id}/stream", include_in_schema=False)
async def stream_run(
    run_id: str,
    analysis_run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> StreamingResponse:
    try:
        analysis_run_service.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Analysis run not found.") from exc

    async def event_generator():
        last_revision = -1
        while True:
            try:
                run = analysis_run_service.get_run(run_id)
            except RunNotFoundError:
                break

            if run.revision != last_revision:
                payload = json.dumps(run.model_dump(mode="json"))
                yield f"id: {run.revision}\nevent: run\ndata: {payload}\n\n"
                last_revision = run.revision

            if run.status in {"completed", "failed"}:
                break

            await asyncio.sleep(0.35)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/analyze-ppt")
async def analyze_presentation(
    file: UploadFile = File(...),
    rubric_json: str = Form(...),
):
    try:
        rubric = json.loads(rubric_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid rubric_json format.") from exc

    filename = file.filename or ""

    if filename.lower().endswith(".pptx"):
        suffix = ".pptx"
    elif filename.lower().endswith(".pdf"):
        suffix = ".pdf"
    else:
        raise HTTPException(
            status_code=400,
            detail="Only .pptx and .pdf files are supported.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    return analyze_ppt(temp_path, rubric)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    analysis_run_service: AnalysisRunService = Depends(get_analysis_run_service),
    github_service: GitHubService = Depends(get_github_service),
    filter_service: FilterService = Depends(get_filter_service),
    context_builder: ContextBuilder = Depends(get_context_builder),
    tree_analysis_service: TreeAnalysisService = Depends(get_tree_analysis_service),
    repository_analysis_service: RepositoryAnalysisService = Depends(
        get_repository_analysis_service
    ),
) -> AnalyzeResponse:
    """Analyze a public GitHub repository end to end across Phase 1, Phase 2, and Phase 3."""

    try:
        result = await analysis_run_service.run_inline(
            request,
            github_service=github_service,
            filter_service=filter_service,
            context_builder=context_builder,
            tree_analysis_service=tree_analysis_service,
            repository_analysis_service=repository_analysis_service,
        )
        logger.info("Repository analysis completed")
        return result
    except InvalidGitHubUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BranchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GitHubTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except MalformedGitHubResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GitHubServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TreeAnalysisParserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RepositoryAnalysisParserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
