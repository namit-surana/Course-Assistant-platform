import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api_ui.router import router as runs_router
from src.config.settings import Settings, get_settings
from src.events.router import router as events_router
from src.jobs.router import router as jobs_router
from src.submissions.router import router as submissions_router
from src.video_agent.router import router as video_analysis_router
from src.utils.logging import configure_logging
from src.voice_agent.services.realtime_bridge import VoiceRealtimeBridge
from src.voice_agent.services.transcript_store import VoiceTranscriptStore


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


OPENAPI_TAGS = [
    {"name": "events", "description": "Evaluation event lifecycle and event-scoped submission listing."},
    {"name": "submissions", "description": "Submission creation, presigned upload orchestration, and detail retrieval."},
    {"name": "jobs", "description": "Unified async job status polling for worker-driven analysis."},
    {"name": "video-analysis", "description": "Video analysis job creation and polling endpoints."},
    {"name": "voice-agent", "description": "Live voice transcript streaming APIs."},
    {"name": "runs", "description": "Live progress for in-process repository analysis runs."},
]

app = FastAPI(
    title="GitHub Repository Analyzer",
    version="3.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(submissions_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(video_analysis_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")


def get_voice_realtime_bridge(
    settings: Settings = Depends(get_settings),
) -> VoiceRealtimeBridge:
    if not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=500,
            detail="ELEVENLABS_API_KEY is not configured.",
        )
    return VoiceRealtimeBridge(
        api_key=settings.elevenlabs_api_key,
        transcript_store=VoiceTranscriptStore(settings.output_dir),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def redirect_root_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.websocket("/api/voice-agent/stream")
async def stream_voice_transcript(
    websocket: WebSocket,
    event_id: str | None = None,
    submission_id: str | None = None,
    language_code: str = "eng",
    voice_bridge: VoiceRealtimeBridge = Depends(get_voice_realtime_bridge),
) -> None:
    await voice_bridge.run(
        client_socket=websocket,
        event_id=event_id,
        submission_id=submission_id,
        language_code=language_code,
    )
