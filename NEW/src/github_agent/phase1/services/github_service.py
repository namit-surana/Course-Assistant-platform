import logging
import json
import hashlib
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse

import httpx

from src.github_agent.phase1.models.schemas import DocumentationFile, RepoMetadata, TreeItem


logger = logging.getLogger(__name__)


class GitHubServiceError(Exception):
    """Base exception for GitHub service failures."""


class InvalidGitHubUrlError(GitHubServiceError):
    """Raised when the provided GitHub URL is invalid."""


class RepositoryNotFoundError(GitHubServiceError):
    """Raised when a repository cannot be found."""


class BranchNotFoundError(GitHubServiceError):
    """Raised when a branch does not exist."""


class GitHubRateLimitError(GitHubServiceError):
    """Raised when the GitHub API rate limit is exceeded."""


class GitHubTimeoutError(GitHubServiceError):
    """Raised when a GitHub API call times out."""


class MalformedGitHubResponseError(GitHubServiceError):
    """Raised when the GitHub API returns an unexpected response payload."""


@dataclass(slots=True)
class GitHubRepoRef:
    owner: str
    repo: str


class GitHubService:
    """Wrapper around GitHub REST API operations used by Phase 1."""

    REPO_METADATA_ENDPOINT = "/repos/{owner}/{repo}"
    RECURSIVE_TREE_ENDPOINT = "/repos/{owner}/{repo}/git/trees/{branch}"
    CONTENTS_ENDPOINT = "/repos/{owner}/{repo}/contents/{path}"

    def __init__(
        self,
        api_base_url: str,
        request_timeout_seconds: float,
        github_token: str | None = None,
        client: httpx.AsyncClient | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds
        self.github_token = github_token
        self._client = client
        self.cache_dir = cache_dir

    async def get_repo_metadata(self, owner: str, repo: str) -> RepoMetadata:
        """Fetch repository metadata from GitHub."""

        payload = await self._request_json(
            "GET",
            self.REPO_METADATA_ENDPOINT.format(owner=owner, repo=repo),
            not_found_error=RepositoryNotFoundError("The requested repository could not be found."),
        )
        try:
            return RepoMetadata(
                full_name=payload["full_name"],
                description=payload.get("description"),
                default_branch=payload["default_branch"],
                language=payload.get("language"),
                size=self._format_repo_size(payload.get("size", 0)),
                stargazers_count=payload.get("stargazers_count", 0),
                forks_count=payload.get("forks_count", 0),
                open_issues_count=payload.get("open_issues_count", 0),
                fork=payload.get("fork", False),
                created_at=payload.get("created_at"),
                updated_at=payload.get("updated_at"),
                pushed_at=payload.get("pushed_at"),
            )
        except KeyError as exc:
            raise MalformedGitHubResponseError("GitHub repository metadata response was malformed.") from exc

    async def get_recursive_tree(self, owner: str, repo: str, branch: str) -> list[TreeItem]:
        """Fetch the recursive tree for the requested branch."""

        payload = await self._request_json(
            "GET",
            self.RECURSIVE_TREE_ENDPOINT.format(owner=owner, repo=repo, branch=branch),
            params={"recursive": 1},
            not_found_error=BranchNotFoundError("The requested branch could not be found."),
        )
        tree = payload.get("tree")
        if not isinstance(tree, list):
            raise MalformedGitHubResponseError("GitHub tree response did not include a valid tree array.")

        try:
            return [TreeItem.model_validate(item) for item in tree]
        except Exception as exc:  # noqa: BLE001
            raise MalformedGitHubResponseError("GitHub tree response included malformed tree items.") from exc

    async def get_file_content(self, owner: str, repo: str, branch: str, path: str) -> DocumentationFile:
        """Fetch and decode a text file from the GitHub contents API."""

        cached = self._load_cached_file(owner, repo, branch, path)
        if cached is not None:
            return cached
        payload = await self._request_json(
            "GET",
            self.CONTENTS_ENDPOINT.format(owner=owner, repo=repo, path=quote(path, safe="/")),
            params={"ref": branch},
            not_found_error=GitHubServiceError(f"The requested file could not be found: {path}"),
        )
        document = self._build_documentation_file(path, payload)
        self._save_cached_file(owner, repo, branch, document)
        return document

    def get_file_preview(
        self,
        owner: str,
        repo: str,
        branch: str,
        path: str,
        *,
        start_line: int = 1,
        max_lines: int = 80,
        max_chars: int = 4000,
    ) -> str:
        """Fetch a bounded text preview for a repository file."""

        document = self._load_cached_file(owner, repo, branch, path)
        if document is None:
            payload = self._request_json_sync(
                "GET",
                self.CONTENTS_ENDPOINT.format(owner=owner, repo=repo, path=quote(path, safe="/")),
                params={"ref": branch},
                not_found_error=GitHubServiceError(f"The requested file could not be found: {path}"),
            )
            document = self._build_documentation_file(path, payload)
            self._save_cached_file(owner, repo, branch, document)

        lines = document.content.splitlines()
        safe_start_line = max(start_line, 1)
        start_index = safe_start_line - 1
        preview_lines = lines[start_index : start_index + max_lines]
        preview = "\n".join(preview_lines).strip()
        if len(preview) > max_chars:
            preview = preview[:max_chars].rstrip()
        if not preview:
            preview = document.content[:max_chars].strip()
        if preview_lines:
            end_line = start_index + len(preview_lines)
        else:
            end_line = safe_start_line - 1
        has_more = len(lines) > end_line
        header = [
            f"Path: {path}",
            f"Lines: {safe_start_line}-{end_line}" if end_line >= safe_start_line else f"Lines: {safe_start_line}-0",
            f"Has more: {'yes' if has_more else 'no'}",
            "",
        ]
        return "\n".join(header) + preview

    def parse_github_url(self, repo_url: str) -> GitHubRepoRef:
        """Parse a GitHub repository URL and extract owner and repo."""

        parsed = urlparse(repo_url)
        if parsed.scheme not in {"http", "https"}:
            raise InvalidGitHubUrlError("GitHub repository URL must start with http:// or https://.")
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise InvalidGitHubUrlError("Only github.com repository URLs are supported.")

        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(path_parts) != 2:
            raise InvalidGitHubUrlError("GitHub repository URL must be in the form https://github.com/owner/repo.")

        owner, repo = path_parts
        if repo.endswith(".git"):
            repo = repo[:-4]
        if not owner or not repo:
            raise InvalidGitHubUrlError("GitHub repository URL is missing owner or repository name.")
        return GitHubRepoRef(owner=owner, repo=repo)

    async def _request_json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        not_found_error: GitHubServiceError | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-analyzer-phase1",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(
                base_url=self.api_base_url,
                timeout=self.request_timeout_seconds,
                headers=headers,
            )
            close_client = True

        try:
            if self._client is not None:
                response = await client.request(method, f"{self.api_base_url}{path}", params=params, headers=headers)
            else:
                response = await client.request(method, path, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("GitHub request timed out")
            raise GitHubTimeoutError("GitHub API request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.error("GitHub request failed")
            raise GitHubServiceError("GitHub API request failed.") from exc
        finally:
            if close_client:
                await client.aclose()

        if response.status_code == 404 and not_found_error is not None:
            raise not_found_error
        if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubRateLimitError("GitHub API rate limit exceeded.")
        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise GitHubServiceError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise MalformedGitHubResponseError("GitHub API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise MalformedGitHubResponseError("GitHub API returned an unexpected response shape.")
        return payload

    def _request_json_sync(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        not_found_error: GitHubServiceError | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-analyzer-phase1",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        with httpx.Client(
            base_url=self.api_base_url,
            timeout=self.request_timeout_seconds,
            headers=headers,
        ) as client:
            try:
                response = client.request(method, path, params=params)
            except httpx.TimeoutException as exc:
                logger.warning("GitHub request timed out")
                raise GitHubTimeoutError("GitHub API request timed out.") from exc
            except httpx.HTTPError as exc:
                logger.error("GitHub request failed")
                raise GitHubServiceError("GitHub API request failed.") from exc

        if response.status_code == 404 and not_found_error is not None:
            raise not_found_error
        if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubRateLimitError("GitHub API rate limit exceeded.")
        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise GitHubServiceError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise MalformedGitHubResponseError("GitHub API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise MalformedGitHubResponseError("GitHub API returned an unexpected response shape.")
        return payload

    def _load_cached_file(self, owner: str, repo: str, branch: str, path: str) -> DocumentationFile | None:
        cache_path = self._cache_path(owner, repo, branch, path)
        if cache_path is None or not cache_path.exists():
            return None

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return DocumentationFile.model_validate(payload)
        except Exception:  # noqa: BLE001
            return None

    def _save_cached_file(self, owner: str, repo: str, branch: str, document: DocumentationFile) -> None:
        cache_path = self._cache_path(owner, repo, branch, document.path)
        if cache_path is None:
            return
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(document.model_dump(mode="json"), indent=2), encoding="utf-8")

    def _cache_path(self, owner: str, repo: str, branch: str, path: str) -> Path | None:
        if self.cache_dir is None:
            return None
        key = hashlib.sha1(f"{owner}:{repo}:{branch}:{path}".encode("utf-8")).hexdigest()
        safe_name = Path(path).name or "file"
        return self.cache_dir / f"{owner}__{repo}__{branch}" / f"{safe_name}__{key}.json"

    @staticmethod
    def _build_documentation_file(path: str, payload: dict[str, Any]) -> DocumentationFile:
        if payload.get("type") != "file":
            raise MalformedGitHubResponseError(f"GitHub contents response for {path} was not a file.")

        encoding = payload.get("encoding")
        content = payload.get("content")
        if encoding != "base64" or not isinstance(content, str):
            raise MalformedGitHubResponseError(f"GitHub contents response for {path} was malformed.")

        try:
            decoded_content = b64decode(content).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            raise MalformedGitHubResponseError(f"Unable to decode GitHub file content for {path}.") from exc

        return DocumentationFile(
            path=path,
            size=payload.get("size"),
            content=decoded_content,
        )

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("message"), str):
                return payload["message"]
        except ValueError:
            pass
        return f"GitHub API request failed with status {response.status_code}."

    @staticmethod
    def _format_repo_size(size_kb: int) -> str:
        if size_kb >= 1024 * 1024:
            return f"{size_kb / (1024 * 1024):.2f} GB"
        if size_kb >= 1024:
            return f"{size_kb / 1024:.2f} MB"
        return f"{size_kb} KB"
