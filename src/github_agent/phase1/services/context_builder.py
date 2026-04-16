import json
from datetime import datetime, timezone
from pathlib import Path

from src.github_agent.phase1.models.schemas import (
    DocumentationFile,
    FilteredRepoContext,
    RepoChunk,
    RepoChunkFileEntry,
    RepoChunkIndexArtifact,
    RepoContextArtifact,
    RepoMetadata,
    TreeItem,
    TreeSummary,
)


class ContextBuilder:
    """Build and persist the Phase 1 repo_context artifact."""

    def __init__(self, output_dir: Path, chunk_size_lines: int = 80) -> None:
        self.output_dir = output_dir
        self.chunk_size_lines = chunk_size_lines

    def build_context(
        self,
        repo_url: str,
        owner: str,
        repo: str,
        branch: str,
        repo_metadata: RepoMetadata,
        tree_items: list[TreeItem],
        filtered_context: FilteredRepoContext,
        documentation_files: list[DocumentationFile],
    ) -> RepoContextArtifact:
        """Build the in-memory repo context artifact."""

        total_blobs = sum(1 for item in tree_items if item.type == "blob")
        total_trees = sum(1 for item in tree_items if item.type == "tree")

        return RepoContextArtifact(
            repo_url=repo_url,
            owner=owner,
            repo=repo,
            branch=branch,
            repo_metadata=repo_metadata,
            tree_summary=TreeSummary(
                total_items=len(tree_items),
                total_blobs=total_blobs,
                total_trees=total_trees,
                filtered_out_count=filtered_context.filtered_out_count,
                selected_file_count=filtered_context.selected_file_count,
            ),
            selected_files=filtered_context.selected_paths,
            filtered_out_files=filtered_context.filtered_out_paths,
            documentation_files=documentation_files,
            created_at=datetime.now(timezone.utc),
        )

    def save_context(self, artifact: RepoContextArtifact) -> Path:
        """Persist the repo context artifact to disk."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{artifact.owner}__{artifact.repo}__repo_context.json"
        output_path.write_text(json.dumps(artifact.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path

    def build_chunk_index(
        self,
        *,
        repo_url: str,
        owner: str,
        repo: str,
        branch: str,
        selected_files: list[DocumentationFile],
    ) -> RepoChunkIndexArtifact:
        entries: list[RepoChunkFileEntry] = []

        for file in selected_files:
            lines = file.content.splitlines()
            chunks: list[RepoChunk] = []
            for start in range(0, len(lines), self.chunk_size_lines):
                chunk_lines = lines[start : start + self.chunk_size_lines]
                start_line = start + 1
                end_line = start + len(chunk_lines)
                chunk_content = "\n".join(chunk_lines)
                chunks.append(
                    RepoChunk(
                        chunk_id=f"{file.path}:{start_line}-{end_line}",
                        start_line=start_line,
                        end_line=end_line,
                        line_count=len(chunk_lines),
                        char_count=len(chunk_content),
                        content=chunk_content,
                    )
                )

            entries.append(
                RepoChunkFileEntry(
                    path=file.path,
                    size=file.size,
                    line_count=len(lines),
                    char_count=len(file.content),
                    chunks=chunks,
                )
            )

        return RepoChunkIndexArtifact(
            repo_url=repo_url,
            owner=owner,
            repo=repo,
            branch=branch,
            selected_file_count=len(selected_files),
            chunk_size_lines=self.chunk_size_lines,
            files=entries,
            created_at=datetime.now(timezone.utc),
        )

    def save_chunk_index(self, artifact: RepoChunkIndexArtifact) -> Path:
        """Persist the repo chunk index artifact to disk."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{artifact.owner}__{artifact.repo}__repo_chunk_index.json"
        output_path.write_text(json.dumps(artifact.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path
