"""Tests pour la récupération du dernier commit GitHub (API mockée)."""

import json
import unittest
from unittest.mock import MagicMock, patch

from app.services.github_last_commit import (
    fetch_last_commit_audit_payload,
    format_payload_for_llm,
)


class TestGitHubLastCommit(unittest.TestCase):
    def test_validation_owner_invalid(self) -> None:
        payload, err = fetch_last_commit_audit_payload("", "repo", "main", token=None)
        self.assertIsNotNone(err)
        self.assertIn("error", payload)

    def test_success_single_file(self) -> None:
        commit_sha = "abc1234" + "0" * 33

        def fake_request(method, path, token, params=None, timeout=45):
            mock = MagicMock()
            if path.endswith("/commits") and params and params.get("per_page") == 1:
                mock.status_code = 200
                mock.json.return_value = [{"sha": commit_sha}]
                mock.raise_for_status = MagicMock()
            elif f"/commits/{commit_sha}" in path:
                mock.status_code = 200
                mock.json.return_value = {
                    "sha": commit_sha,
                    "html_url": f"https://github.com/o/r/commit/{commit_sha}",
                    "commit": {
                        "message": "fix: thing",
                        "author": {"name": "Dev", "date": "2026-01-01T00:00:00Z"},
                    },
                    "files": [
                        {
                            "filename": "app.py",
                            "status": "modified",
                            "additions": 2,
                            "deletions": 1,
                            "patch": "@@ -1 +1 @@\n-old\n+new",
                        }
                    ],
                }
                mock.raise_for_status = MagicMock()
            else:
                mock.status_code = 404
                mock.json.return_value = {}
            return mock

        with patch("app.services.github_last_commit._request", side_effect=fake_request):
            payload, err = fetch_last_commit_audit_payload("o", "r", "main", token=None)

        self.assertIsNone(err)
        self.assertEqual(payload["commit"]["short_sha"], commit_sha[:7])
        self.assertEqual(len(payload["files"]), 1)
        self.assertEqual(payload["files"][0]["filename"], "app.py")
        s = format_payload_for_llm(payload)
        self.assertIn("app.py", s)
        data = json.loads(s)
        self.assertEqual(data["commit"]["repository"], "o/r")

    def test_empty_branch(self) -> None:
        with patch("app.services.github_last_commit._request") as m:
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = []
            mock.raise_for_status = MagicMock()
            m.return_value = mock
            payload, err = fetch_last_commit_audit_payload("o", "r", "empty", token=None)
        self.assertEqual(err, "empty")
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
