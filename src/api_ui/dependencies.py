from __future__ import annotations

from functools import lru_cache

from src.api_ui.services.analysis_run_service import AnalysisRunService
from src.api_ui.services.run_store import AnalysisRunStore


@lru_cache(maxsize=1)
def get_run_store() -> AnalysisRunStore:
    return AnalysisRunStore()


@lru_cache(maxsize=1)
def get_analysis_run_service() -> AnalysisRunService:
    return AnalysisRunService(get_run_store())
