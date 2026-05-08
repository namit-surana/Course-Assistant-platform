from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api_ui.dependencies import get_run_store
from src.api_ui.models.schemas import AnalysisRunState
from src.api_ui.services.run_store import AnalysisRunStore, RunNotFoundError


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=AnalysisRunState)
def get_run(
    run_id: str,
    store: AnalysisRunStore = Depends(get_run_store),
) -> AnalysisRunState:
    try:
        return store.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found.") from exc
