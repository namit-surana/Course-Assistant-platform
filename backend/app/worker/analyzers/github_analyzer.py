from github import Github
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)


def fetch_repo_summary(github_url: str) -> dict:
    """Fetch key metadata and files from a GitHub repo."""
    g = Github(settings.GITHUB_TOKEN or None)

    # Extract owner/repo from URL
    parts = github_url.rstrip("/").split("/")
    owner, repo_name = parts[-2], parts[-1]
    repo = g.get_repo(f"{owner}/{repo_name}")

    readme = ""
    try:
        readme = repo.get_readme().decoded_content.decode("utf-8")[:3000]
    except Exception:
        readme = "No README found."

    languages = repo.get_languages()
    commits = repo.get_commits().totalCount
    file_tree = [f.path for f in repo.get_git_tree("HEAD", recursive=True).tree[:60]]

    return {
        "name": repo.name,
        "description": repo.description,
        "stars": repo.stargazers_count,
        "languages": languages,
        "commit_count": commits,
        "file_tree": file_tree,
        "readme": readme,
    }


def analyze_github(github_url: str, rubric_criteria: list) -> dict:
    """Analyze a GitHub repo against rubric criteria using Gemini."""
    repo_data = fetch_repo_summary(github_url)
    criteria_text = "\n".join(
        [f"- {c['category']} (max {c['max_score']} pts): {c['description']}" for c in rubric_criteria]
    )

    prompt = f"""
You are an academic evaluator reviewing a student project GitHub repository.

REPOSITORY INFO:
Name: {repo_data['name']}
Description: {repo_data['description']}
Languages: {repo_data['languages']}
Total Commits: {repo_data['commit_count']}
File Tree (first 60 files): {repo_data['file_tree']}

README:
{repo_data['readme']}

RUBRIC CRITERIA:
{criteria_text}

For each criterion, provide a score and explanation based on the repository.

Respond in JSON format:
{{
  "criteria_scores": [
    {{
      "category": "<criterion name>",
      "score": <number>,
      "comment": "<explanation>"
    }}
  ],
  "github_summary": "<2-3 sentence summary of the repository quality>"
}}
"""
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    return {"raw": response.text}
