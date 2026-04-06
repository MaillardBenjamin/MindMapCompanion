"""Tests unitaires (sans Playwright réel) pour la supervision de site."""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

from app.services.site_health_check import (
    validate_steps,
    quick_http_check,
    repair_playwright_steps_llm,
    run_site_health_check,
    sanitize_failure_meta_for_client,
)
from app.tools.site_health_check_tools import SiteHealthCheckTools


class TestSiteHealthCheck(unittest.TestCase):
    def test_validate_rejects_unknown_action(self) -> None:
        self.assertIsNotNone(validate_steps([{"action": "hack_the_planet"}]))

    def test_validate_accepts_minimal_plan(self) -> None:
        steps = [
            {"action": "click", "selector": "text=OK"},
            {"action": "expect_visible", "selector": "#footer"},
        ]
        self.assertIsNone(validate_steps(steps))

    def test_validate_accepts_role_has_text(self) -> None:
        steps = [
            {"action": "wait_for_selector", "role": "link", "has_text": "Déconnexion"},
            {"action": "click", "role": "link", "name": "Déconnexion"},
            {"action": "click", "role": "button", "name": "Accepter tout"},
        ]
        self.assertIsNone(validate_steps(steps))

    def test_validate_rejects_role_without_name_or_has_text(self) -> None:
        err = validate_steps([{"action": "click", "role": "link"}])
        self.assertIsNotNone(err)
        self.assertIn("selector", err.lower() or err)

    def test_sanitize_failure_meta_strips_png(self) -> None:
        png = b"\x89PNG\r\n\x1a\nfake"
        meta = {
            "failed_step_1based": 1,
            "screenshot_png": png,
        }
        clean = sanitize_failure_meta_for_client(meta)
        self.assertNotIn("screenshot_png", clean)
        self.assertTrue(clean.get("failure_screenshot_captured"))
        self.assertEqual(clean.get("failure_screenshot_bytes"), len(png))

    def test_quick_http_mock_200(self) -> None:
        with patch("app.services.site_health_check.requests.get") as g:
            m = MagicMock()
            m.status_code = 200
            m.content = b"ok"
            g.return_value = m
            ok, detail = quick_http_check("https://example.com")
        self.assertTrue(ok)
        self.assertIn("200", detail)

    def test_run_invalid_url_alerts(self) -> None:
        out = run_site_health_check(
            "not-a-url",
            "do thing",
            alert_email="a@b.co",
        )
        self.assertIn("error", out)
        self.assertIs(out.get("http_ok"), None)

    @patch("app.services.site_health_check.nl_to_playwright_steps")
    @patch("app.services.site_health_check.get_settings")
    @patch("app.services.site_health_check.quick_http_check")
    @patch("app.services.site_health_check.run_playwright_sync")
    @patch("app.services.site_health_check.repair_playwright_steps_llm")
    def test_self_heal_second_run_succeeds(
        self, mock_repair, mock_pw, mock_http, mock_settings, mock_nl
    ) -> None:
        mock_settings.return_value = Mock(
            skip_agent_llm=False,
            site_health_max_repairs=2,
        )
        mock_http.return_value = (True, "HTTP 200")
        mock_nl.return_value = (
            [{"action": "click", "selector": "text=bad"}],
            None,
        )
        meta = {
            "failed_step_1based": 1,
            "failed_action": "click",
            "failed_step": {"action": "click", "selector": "text=bad"},
            "page_url": "https://example.com/",
            "page_title": "Ex",
        }
        mock_pw.side_effect = [
            (False, "TimeoutError", ["step 1 click FAIL"], meta),
            (True, "Scénario OK", ["step 1 click ok"], None),
        ]
        mock_repair.return_value = (
            [{"action": "click", "selector": "text=OK"}],
            None,
        )
        out = run_site_health_check(
            "https://example.com",
            "cliquer OK",
            alert_email="",
        )
        self.assertTrue(out.get("playwright_ok"))
        self.assertEqual(out.get("playwright_repair_rounds"), 1)
        self.assertEqual(mock_pw.call_count, 2)
        mock_repair.assert_called_once()

    @patch("app.services.site_health_check.get_settings")
    @patch("app.services.site_health_check.get_agno_chat_model")
    @patch("app.services.site_health_check.Agent")
    def test_repair_llm_parses_json(self, mock_agent_cls, mock_model, mock_get_settings) -> None:
        mock_get_settings.return_value = Mock(skip_agent_llm=False)
        mock_model.return_value = MagicMock()
        resp = MagicMock()
        resp.content = '[{"action":"click","selector":"text=Fixed"}]'
        mock_agent_cls.return_value.run.return_value = resp
        steps, err = repair_playwright_steps_llm(
            "https://example.com",
            "cliquer",
            [{"action": "click", "selector": "text=Bad"}],
            {
                "failed_step_1based": 1,
                "failed_action": "click",
                "page_url": "https://example.com/",
                "page_title": "T",
            },
            "TimeoutError",
        )
        self.assertIsNone(err)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].get("selector"), "text=Fixed")

    @patch("app.services.site_health_check.get_settings")
    @patch("app.services.site_health_check.get_agno_chat_model")
    @patch("app.services.site_health_check.Agent")
    def test_repair_llm_sends_screenshot_to_agent(
        self, mock_agent_cls, mock_model, mock_get_settings
    ) -> None:
        mock_get_settings.return_value = Mock(
            skip_agent_llm=False,
            site_health_repair_with_screenshot=True,
        )
        mock_model.return_value = MagicMock()
        resp = MagicMock()
        resp.content = '[{"action":"click","selector":"text=OK"}]'
        mock_agent_cls.return_value.run.return_value = resp
        meta = {
            "failed_step_1based": 1,
            "failed_action": "click",
            "page_url": "https://example.com/",
            "page_title": "T",
            "screenshot_png": b"\x89PNG\r\n\x1a\nx",
        }
        repair_playwright_steps_llm(
            "https://example.com",
            "go",
            [{"action": "click", "selector": "text=Bad"}],
            meta,
            "Timeout",
        )
        mock_run = mock_agent_cls.return_value.run
        self.assertEqual(mock_run.call_count, 1)
        _, kwargs = mock_run.call_args
        self.assertIsNotNone(kwargs.get("images"))
        self.assertEqual(len(kwargs["images"]), 1)


class TestSiteHealthCheckTools(unittest.TestCase):
    @staticmethod
    def _tools_minimal(agent_config: dict):
        """Installe l’objet sans __init__ Agno (incompatible en tests avec certaines versions)."""
        t = SiteHealthCheckTools.__new__(SiteHealthCheckTools)
        t.agent_config = agent_config
        return t

    def test_resolve_headless_accepts_bool(self) -> None:
        tools = self._tools_minimal({"site_check_headless": True})
        self.assertFalse(tools._resolve_headless(True))
        self.assertTrue(tools._resolve_headless(False))

    @patch("app.tools.site_health_check_tools.run_site_health_check")
    def test_verify_site_health_accepts_show_browser_bool(self, mock_run) -> None:
        mock_run.return_value = {
            "http_ok": True,
            "playwright_ok": True,
            "alert_sent": False,
        }
        tools = self._tools_minimal({"alert_email": "x@y.z", "site_check_headless": True})
        # Agno enveloppe la méthode : l’entrée pydantic-validée est .entrypoint.
        out = tools.verify_site_health.entrypoint(
            tools,
            "https://example.com",
            "",
            "",
            "",
            True,
        )
        self.assertTrue(json.loads(out)["http_ok"])
        mock_run.assert_called_once()
        self.assertFalse(mock_run.call_args.kwargs["headless"])


if __name__ == "__main__":
    unittest.main()
