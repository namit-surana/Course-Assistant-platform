import pytest

from src.github_agent.phase1.services.github_service import GitHubService, InvalidGitHubUrlError


@pytest.fixture
def github_service() -> GitHubService:
    return GitHubService(api_base_url="https://api.github.com", request_timeout_seconds=20)


@pytest.mark.parametrize(
    ("url", "owner", "repo"),
    [
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
        ("https://www.github.com/openai/openai-python/", "openai", "openai-python"),
    ],
)
def test_parse_github_url_valid(url: str, owner: str, repo: str, github_service: GitHubService) -> None:
    result = github_service.parse_github_url(url)
    assert result.owner == owner
    assert result.repo == repo


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "https://gitlab.com/octocat/Hello-World",
        "https://github.com/octocat",
        "https://github.com/octocat/Hello-World/issues",
    ],
)
def test_parse_github_url_invalid(url: str, github_service: GitHubService) -> None:
    with pytest.raises(InvalidGitHubUrlError):
        github_service.parse_github_url(url)
