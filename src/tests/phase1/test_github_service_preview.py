import pytest

from src.github_agent.phase1.models.schemas import DocumentationFile
from src.github_agent.phase1.services.github_service import GitHubService


@pytest.mark.asyncio
async def test_get_file_content_uses_local_cache(workspace_tmp_path):
    service = GitHubService(
        api_base_url="https://api.github.com",
        request_timeout_seconds=5,
        cache_dir=workspace_tmp_path / "file_cache",
    )
    calls = {"count": 0}

    async def fake_request_json(method, path, params=None, not_found_error=None):
        calls["count"] += 1
        return {
            "type": "file",
            "encoding": "base64",
            "content": "IyBIZWxsbwo=",
            "size": 8,
        }

    service._request_json = fake_request_json  # type: ignore[method-assign]

    first = await service.get_file_content("octocat", "Hello-World", "main", "README.md")
    second = await service.get_file_content("octocat", "Hello-World", "main", "README.md")

    assert isinstance(first, DocumentationFile)
    assert first.content == "# Hello\n"
    assert second.content == "# Hello\n"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_get_file_content_handles_binary_payload(workspace_tmp_path):
    service = GitHubService(
        api_base_url="https://api.github.com",
        request_timeout_seconds=5,
        cache_dir=workspace_tmp_path / "file_cache",
    )

    async def fake_request_json(method, path, params=None, not_found_error=None):
        return {
            "type": "file",
            "encoding": "base64",
            "content": "APkA",  # Includes non-UTF8 bytes when decoded.
            "size": 3,
        }

    service._request_json = fake_request_json  # type: ignore[method-assign]

    document = await service.get_file_content("octocat", "Hello-World", "main", "fonts/agustina.otf")

    assert isinstance(document, DocumentationFile)
    assert document.path == "fonts/agustina.otf"
    assert document.content == ""


def test_get_file_preview_supports_start_line_and_cache(workspace_tmp_path):
    service = GitHubService(
        api_base_url="https://api.github.com",
        request_timeout_seconds=5,
        cache_dir=workspace_tmp_path / "file_cache",
    )
    calls = {"count": 0}

    def fake_request_json_sync(method, path, params=None, not_found_error=None):
        calls["count"] += 1
        return {
            "type": "file",
            "encoding": "base64",
            "content": "bGluZTEKbGluZTIKbGluZTMKbGluZTQK",
            "size": 24,
        }

    service._request_json_sync = fake_request_json_sync  # type: ignore[method-assign]

    first = service.get_file_preview("octocat", "Hello-World", "main", "src/main.py", start_line=2, max_lines=2)
    second = service.get_file_preview("octocat", "Hello-World", "main", "src/main.py", start_line=3, max_lines=1)

    assert "Lines: 2-3" in first
    assert "line2\nline3" in first
    assert "Has more: yes" in first
    assert "Lines: 3-3" in second
    assert "line3" in second
    assert calls["count"] == 1
