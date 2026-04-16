import json
from pathlib import Path

from src.github_agent.phase2.models.schemas import Phase1RepoContextInput


class Phase2Loader:
    """Load and validate Phase 1 artifacts for Phase 2 processing."""

    def load_phase1_artifact(self, repo_context_path: str | Path) -> Phase1RepoContextInput:
        """Read a Phase 1 artifact from disk and validate its schema."""

        path = Path(repo_context_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Phase1RepoContextInput.model_validate(payload)
