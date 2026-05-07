from __future__ import annotations

from pathlib import PurePosixPath

from src.github_agent.phase1.models.schemas import FilteredRepoContext, TreeItem


EXCLUDED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "vendor",
    "target",
    "out",
    ".idea",
    ".vscode",
}

EXCLUDED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".jar",
    ".exe",
    ".dll",
    ".so",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".mp4",
    ".mov",
    ".avi",
    ".webm",
    ".class",
}

EXCLUDED_SUFFIX_PATTERNS = (".min.js", ".bundle.js", ".map")


class FilterService:
    """Deterministic tree filtering service."""

    def __init__(self, max_file_size_bytes: int) -> None:
        self.max_file_size_bytes = max_file_size_bytes

    def should_exclude_path(self, path: str, size: int | None = None) -> tuple[bool, list[str]]:
        """Return whether a path should be excluded and why."""

        reasons: list[str] = []
        pure_path = PurePosixPath(path)

        if any(part in EXCLUDED_DIRECTORIES for part in pure_path.parts):
            reasons.append("excluded_directory")
        if pure_path.suffix.lower() in EXCLUDED_EXTENSIONS:
            reasons.append("excluded_extension")
        if any(path.lower().endswith(pattern) for pattern in EXCLUDED_SUFFIX_PATTERNS):
            reasons.append("excluded_pattern")
        if size is not None and size > self.max_file_size_bytes:
            reasons.append("file_too_large")

        return (len(reasons) > 0, reasons)

    def filter_tree(self, tree_items: list[TreeItem]) -> FilteredRepoContext:
        """Split blob files into selected and filtered-out lists."""

        excluded_files: list[TreeItem] = []
        selected_files: list[TreeItem] = []
        exclusion_reasons: dict[str, list[str]] = {}

        for item in tree_items:
            if item.type != "blob":
                continue
            should_exclude, reasons = self.should_exclude_path(item.path, item.size)
            if should_exclude:
                excluded_files.append(item)
                exclusion_reasons[item.path] = reasons
                continue
            selected_files.append(item)

        selected_files.sort(key=lambda item: (item.path.count("/"), item.path.lower()))
        excluded_files.sort(key=lambda item: (item.path.count("/"), item.path.lower()))

        return FilteredRepoContext(
            selected_files=selected_files,
            excluded_files=excluded_files,
            selected_paths=[item.path for item in selected_files],
            filtered_out_paths=[item.path for item in excluded_files],
            filtered_out_count=len(excluded_files),
            selected_file_count=len(selected_files),
            exclusion_reasons=exclusion_reasons,
        )


_DEFAULT_FILTER_SERVICE = FilterService(max_file_size_bytes=200_000)


def should_exclude_path(path: str) -> tuple[bool, list[str]]:
    """Module-level helper for deterministic path exclusion checks."""

    return _DEFAULT_FILTER_SERVICE.should_exclude_path(path)


def filter_tree(tree_items: list[TreeItem]) -> FilteredRepoContext:
    """Module-level helper for default tree filtering."""

    return _DEFAULT_FILTER_SERVICE.filter_tree(tree_items)
