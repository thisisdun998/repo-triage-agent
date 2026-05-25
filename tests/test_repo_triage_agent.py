import unittest

from repo_triage_agent.agent import RepoSnapshot, TriageAgent, parse_repo_target, render_markdown


class RepoTriageAgentTest(unittest.TestCase):
    def test_parse_repo_target_accepts_url_and_slug(self):
        self.assertEqual(parse_repo_target("https://github.com/openai/codex"), ("openai", "codex"))
        self.assertEqual(parse_repo_target("openai/codex"), ("openai", "codex"))

    def test_agent_classifies_issues_and_picks_beginner_tasks(self):
        snapshot = RepoSnapshot(
            owner="acme",
            name="demo",
            description="Small command line tool",
            readme="# Demo\n\nInstall with pip.\n\nUsage: demo run",
            file_paths=["README.md", "pyproject.toml", "demo/cli.py", "tests/test_cli.py"],
            issues=[
                {"number": 1, "title": "Crash when config file is missing", "labels": ["bug"]},
                {"number": 2, "title": "Add JSON output", "labels": ["enhancement", "good first issue"]},
                {"number": 3, "title": "How to set token?", "labels": ["question"]},
            ],
            commits=[{"sha": "abc1234", "message": "Add CLI"}],
        )

        report = TriageAgent().run(snapshot)

        self.assertEqual(report.project_type, "Python CLI")
        self.assertEqual([issue.number for issue in report.issue_groups["bug"]], [1])
        self.assertEqual([issue.number for issue in report.beginner_issues], [2])
        self.assertIn("Document the next release scope", report.next_actions)

    def test_render_markdown_contains_agent_reasoning_sections(self):
        snapshot = RepoSnapshot(
            owner="acme",
            name="demo",
            description="",
            readme="# Demo",
            file_paths=["README.md"],
            issues=[],
            commits=[],
        )

        markdown = render_markdown(TriageAgent().run(snapshot))

        self.assertIn("# Repo Triage Report: acme/demo", markdown)
        self.assertIn("## Agent Reasoning", markdown)
        self.assertIn("## Recommended Next Actions", markdown)


if __name__ == "__main__":
    unittest.main()
