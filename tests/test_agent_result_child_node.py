"""Tests pour le rendu markdown des sorties structurées d'agents (News Monitor)."""

from app.services.agent_result_child_node import (
    extract_markdown_from_agent_output,
    parse_news_monitor_plaintext,
)


def test_extract_prefers_output_raw():
    out = {"output_raw": "# Titre\n\nCorps", "output_parsed": {"theme": "x"}}
    assert extract_markdown_from_agent_output(out) == "# Titre\n\nCorps"


def test_extract_prefers_markdown_field_in_parsed():
    out = {
        "output_parsed": {
            "markdown": "## Rapport\n\nTexte.",
            "executive_summary": "ignored",
        }
    }
    assert extract_markdown_from_agent_output(out) == "## Rapport\n\nTexte."


def test_extract_news_monitor_full_sections_french_headings():
    out = {
        "output_parsed": {
            "theme": "Veille climat",
            "executive_summary": "Synthèse courte.",
            "key_findings": [
                {
                    "title": "Point A",
                    "description": "Détail A.",
                    "importance": "high",
                    "source": "Reuters",
                    "date": "2026-04-01",
                }
            ],
            "trends": [
                {
                    "trend_name": "Tendance 1",
                    "description": "Desc.",
                    "direction": "growing",
                    "impact": "Fort",
                }
            ],
            "sources": [
                {
                    "name": "MSCI",
                    "url": "https://example.com",
                    "reliability": "high",
                    "type": "research",
                }
            ],
            "recommendations": [
                {
                    "action": "Surveiller X",
                    "rationale": "Parce que Y.",
                    "priority": "urgent",
                }
            ],
            "next_steps": "Étape 1\nÉtape 2",
            "report_date": "2026-04-04",
        }
    }
    md = extract_markdown_from_agent_output(out)
    assert md is not None
    assert "## Veille climat" in md
    assert "### Résumé exécutif" in md
    assert "### Points clés" in md
    assert "**Point A**" in md
    assert "Importance : élevée" in md
    assert "### Tendances" in md
    assert "Direction : en croissance" in md
    assert "### Sources" in md
    assert "recherche" in md
    assert "fiabilité : élevée" in md
    assert "### Recommandations" in md
    assert "priorité : urgente" in md
    assert "### Prochaines étapes" in md
    assert "Étape 1" in md
    assert "*Date du rapport : 2026-04-04*" in md
    assert "```json" not in md


def test_extract_falls_back_to_json_when_not_news_shape():
    out = {"output_parsed": {"foo": 1, "bar": "baz"}}
    md = extract_markdown_from_agent_output(out)
    assert md is not None
    assert "```json" in md
    assert '"foo": 1' in md


def test_extract_prefers_structured_french_over_raw():
    out = {
        "output_raw": "theme\n\ndump brut à masquer",
        "output_parsed": {
            "theme": "Titre FR",
            "executive_summary": "Résumé FR",
        },
    }
    md = extract_markdown_from_agent_output(out)
    assert md is not None
    assert "### Résumé exécutif" in md
    assert "Résumé FR" in md
    assert "dump brut à masquer" not in md


def test_parse_news_monitor_plaintext_multiline_description():
    raw = """Destinataire : Benjamin

theme

Mon thème

executive_summary

Ma synthèse.

key_findings
title: Un point
description: Détail ligne 1
suite importance
importance: high
source: Test
date: 2026-01-01
"""
    d = parse_news_monitor_plaintext(raw)
    assert d is not None
    assert d["theme"] == "Mon thème"
    assert d["executive_summary"] == "Ma synthèse."
    assert len(d["key_findings"]) == 1
    assert d["key_findings"][0]["title"] == "Un point"
    assert "Détail ligne 1" in d["key_findings"][0]["description"]
    assert "suite importance" in d["key_findings"][0]["description"]
    assert d["key_findings"][0]["importance"] == "high"
