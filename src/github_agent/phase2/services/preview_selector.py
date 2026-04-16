from src.github_agent.phase2.models.schemas import Phase1RepoContextInput, TreeAnalysisInput


class PreviewSelector:
    """Prepare a compact, agent-friendly Phase 2 analysis payload."""

    def build_analysis_input(self, repo_context: Phase1RepoContextInput) -> TreeAnalysisInput:
        """Extract the subset of Phase 1 data the Tree Analysis Agent should see."""

        return TreeAnalysisInput(
            repo_url=repo_context.repo_url,
            owner=repo_context.owner,
            repo=repo_context.repo,
            branch=repo_context.branch,
            repo_metadata=repo_context.repo_metadata,
            tree_summary=repo_context.tree_summary,
            selected_files=sorted(
                dict.fromkeys(path for path in repo_context.selected_files if path),
                key=lambda path: (path.count("/"), path.lower()),
            ),
            documentation_previews=repo_context.documentation_files,
            guaranteed_coverage_metadata=repo_context.preview_content,
        )
