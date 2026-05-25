from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepoSnapshot:
    owner: str
    name: str
    description: str
    readme: str
    file_paths: list[str]
    issues: list[dict[str, Any]]
    commits: list[dict[str, str]]


@dataclass(frozen=True)
class TriageIssue:
    number: int
    title: str
    labels: list[str]
    category: str


@dataclass(frozen=True)
class TriageReport:
    owner: str
    name: str
    description: str
    project_type: str
    readme_score: int
    readme_missing: list[str]
    issue_groups: dict[str, list[TriageIssue]]
    beginner_issues: list[TriageIssue]
    recent_commits: list[str]
    next_actions: list[str]
    reasoning: list[str] = field(default_factory=list)


def parse_repo_target(target: str) -> tuple[str, str]:
    value = target.strip().removesuffix("/")
    match = re.match(r"^(?:https://github\.com/)?([^/\s]+)/([^/\s]+?)(?:\.git)?$", value)
    if not match:
        raise ValueError("Use a GitHub URL like https://github.com/owner/repo or owner/repo.")
    return match.group(1), match.group(2)


class TriageAgent:
    """A small deterministic agent for open-source repository triage."""

    def run(self, snapshot: RepoSnapshot) -> TriageReport:
        issues = [self._issue_from_payload(issue) for issue in snapshot.issues]
        groups = {name: [] for name in ["bug", "feature", "docs", "question", "maintenance"]}
        for issue in issues:
            groups[issue.category].append(issue)

        readme_score, readme_missing = self._score_readme(snapshot.readme)
        next_actions = self._plan_actions(groups, readme_missing, snapshot.file_paths)

        return TriageReport(
            owner=snapshot.owner,
            name=snapshot.name,
            description=snapshot.description,
            project_type=self._detect_project_type(snapshot.file_paths),
            readme_score=readme_score,
            readme_missing=readme_missing,
            issue_groups=groups,
            beginner_issues=[issue for issue in issues if self._is_beginner_friendly(issue)],
            recent_commits=[commit["message"] for commit in snapshot.commits[:5] if commit.get("message")],
            next_actions=next_actions,
            reasoning=[
                "Perceived repository signals from README, file tree, open issues, and recent commits.",
                "Grouped issues by maintainer intent instead of raw labels only.",
                "Selected next actions that reduce onboarding friction before adding new scope.",
            ],
        )

    def _issue_from_payload(self, payload: dict[str, Any]) -> TriageIssue:
        labels = [str(label).lower() for label in payload.get("labels", [])]
        title = str(payload.get("title", "")).strip()
        return TriageIssue(
            number=int(payload.get("number", 0)),
            title=title,
            labels=labels,
            category=self._classify_issue(title, labels),
        )

    def _classify_issue(self, title: str, labels: list[str]) -> str:
        text = f"{title} {' '.join(labels)}".lower()
        if any(word in text for word in ["bug", "crash", "error", "fail", "broken"]):
            return "bug"
        if any(word in text for word in ["doc", "readme", "typo", "example"]):
            return "docs"
        if any(word in text for word in ["question", "how", "why", "help"]):
            return "question"
        if any(word in text for word in ["feature", "enhancement", "add", "support"]):
            return "feature"
        return "maintenance"

    def _is_beginner_friendly(self, issue: TriageIssue) -> bool:
        text = f"{issue.title} {' '.join(issue.labels)}".lower()
        return any(word in text for word in ["good first issue", "help wanted", "docs", "typo", "readme", "simple"])

    def _score_readme(self, readme: str) -> tuple[int, list[str]]:
        text = readme.lower()
        checks = {
            "installation": ["install", "setup", "pip ", "npm ", "cargo "],
            "usage": ["usage", "quickstart", "example", "cli"],
            "testing": ["test", "pytest", "unittest", "npm test"],
            "contributing": ["contributing", "development", "pull request"],
        }
        missing = [name for name, words in checks.items() if not any(word in text for word in words)]
        return round((len(checks) - len(missing)) / len(checks) * 100), missing

    def _detect_project_type(self, file_paths: list[str]) -> str:
        names = {path.lower() for path in file_paths}
        if "package.json" in names:
            return "JavaScript/TypeScript"
        if "go.mod" in names:
            return "Go"
        if "cargo.toml" in names:
            return "Rust"
        if "pyproject.toml" in names or "setup.py" in names:
            if any(path.endswith(("cli.py", "__main__.py")) for path in names):
                return "Python CLI"
            return "Python"
        return "Unknown"

    def _plan_actions(
        self,
        groups: dict[str, list[TriageIssue]],
        readme_missing: list[str],
        file_paths: list[str],
    ) -> list[str]:
        actions = []
        if readme_missing:
            actions.append(f"Improve README sections: {', '.join(readme_missing)}.")
        if groups["bug"]:
            actions.append("Fix the oldest reproducible bug before accepting feature work.")
        actions.append("Document the next release scope")
        if not any(path.startswith("tests/") or "/tests/" in path for path in file_paths):
            actions.append("Add at least one smoke test so future triage can trust changes.")
        return actions


def render_markdown(report: TriageReport) -> str:
    lines = [
        f"# Repo Triage Report: {report.owner}/{report.name}",
        "",
        f"- Project type: {report.project_type}",
        f"- Description: {report.description or 'No description provided'}",
        f"- README completeness: {report.readme_score}/100",
        "",
        "## Agent Reasoning",
        "",
    ]
    lines.extend(f"- {step}" for step in report.reasoning)
    lines.extend(["", "## Issue Triage", ""])
    for category, issues in report.issue_groups.items():
        lines.append(f"### {category.title()} ({len(issues)})")
        if issues:
            lines.extend(f"- #{issue.number} {issue.title}" for issue in issues)
        else:
            lines.append("- No open issues in this category.")
        lines.append("")

    lines.extend(["## Beginner Friendly Issues", ""])
    if report.beginner_issues:
        lines.extend(f"- #{issue.number} {issue.title}" for issue in report.beginner_issues)
    else:
        lines.append("- No obvious beginner-friendly issue found.")

    lines.extend(["", "## Recent Commit Signals", ""])
    if report.recent_commits:
        lines.extend(f"- {message}" for message in report.recent_commits)
    else:
        lines.append("- No recent commit data available.")

    lines.extend(["", "## Recommended Next Actions", ""])
    lines.extend(f"{index}. {action}" for index, action in enumerate(report.next_actions, start=1))
    lines.append("")
    return "\n".join(lines)


def fetch_github_snapshot(owner: str, name: str) -> RepoSnapshot:
    repo = _github_json(f"/repos/{owner}/{name}")
    default_branch = repo.get("default_branch", "main")
    tree = _github_json(f"/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1")
    issues = _github_json(f"/repos/{owner}/{name}/issues?state=open&per_page=50")
    commits = _github_json(f"/repos/{owner}/{name}/commits?per_page=10")

    return RepoSnapshot(
        owner=owner,
        name=name,
        description=repo.get("description") or "",
        readme=_readme(owner, name),
        file_paths=[item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"],
        issues=[
            {
                "number": issue["number"],
                "title": issue["title"],
                "labels": [label["name"] for label in issue.get("labels", [])],
            }
            for issue in issues
            if "pull_request" not in issue
        ],
        commits=[
            {
                "sha": commit.get("sha", "")[:7],
                "message": commit.get("commit", {}).get("message", "").splitlines()[0],
            }
            for commit in commits
        ],
    )


def sample_snapshot() -> RepoSnapshot:
    return RepoSnapshot(
        owner="example",
        name="repo-triage-demo",
        description="Demo repository for agent-based maintainer triage",
        readme="# Demo\n\nInstall with pip.\n\nUsage: repo-triage-agent owner/repo",
        file_paths=["README.md", "pyproject.toml", "repo_triage_agent/__main__.py", "tests/test_agent.py"],
        issues=[
            {"number": 7, "title": "Crash when GitHub rate limit is reached", "labels": ["bug"]},
            {"number": 8, "title": "Add JSON output for CI usage", "labels": ["enhancement", "good first issue"]},
            {"number": 9, "title": "Document token setup in README", "labels": ["docs"]},
        ],
        commits=[{"sha": "a1b2c3d", "message": "Add initial CLI"}],
    )


def _readme(owner: str, name: str) -> str:
    try:
        payload = _github_json(f"/repos/{owner}/{name}/readme")
    except RuntimeError:
        return ""
    encoded = payload.get("content", "")
    if not encoded:
        return ""
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def _github_json(path: str) -> Any:
    request = urllib.request.Request(f"https://api.github.com{path}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "repo-triage-agent")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API returned {exc.code} for {path}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach GitHub API: {exc.reason}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an agentic maintainer triage report for a GitHub repo.")
    parser.add_argument("target", nargs="?", help="GitHub URL or owner/repo slug.")
    parser.add_argument("--sample", action="store_true", help="Run against a built-in offline sample repository.")
    parser.add_argument("--output", "-o", help="Write the markdown report to a file.")
    args = parser.parse_args(argv)

    try:
        if args.sample:
            snapshot = sample_snapshot()
        elif args.target:
            owner, repo = parse_repo_target(args.target)
            snapshot = fetch_github_snapshot(owner, repo)
        else:
            parser.error("provide a GitHub repo target or use --sample")

        markdown = render_markdown(TriageAgent().run(snapshot))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(markdown)
        else:
            sys.stdout.write(markdown)
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
