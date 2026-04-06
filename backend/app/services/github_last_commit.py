"""
Récupération du dernier commit et des diffs via l'API REST GitHub (api.github.com).

Dépôts publics : pas de jeton requis (limite de débit plus basse).
Dépôts privés ou quotas : définir GITHUB_TOKEN (PAT fine-grained ou classic repo read).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Segments GitHub (owner, repo) : alphanum, tiret, point, underscore
_SEGMENT_RE = re.compile(r"^[\w.-]{1,200}$")
# Branche / tag : slash autorisé, pas de traversée
_BRANCH_RE = re.compile(r"^[\w./+-]{1,255}$")


def _valid_owner_repo_branch(owner: str, repo: str, branch: str) -> Optional[str]:
    o, r, b = (owner or "").strip(), (repo or "").strip(), (branch or "main").strip()
    if not o or not _SEGMENT_RE.match(o):
        return "owner invalide (caractères autorisés : lettres, chiffres, . - _)."
    if not r or not _SEGMENT_RE.match(r):
        return "repo invalide (caractères autorisés : lettres, chiffres, . - _)."
    if not b or not _BRANCH_RE.match(b) or ".." in b or b.startswith("/"):
        return "branche invalide."
    return None


def _request(
    method: str,
    path: str,
    token: Optional[str],
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 45,
) -> requests.Response:
    url = f"{GITHUB_API}{path}"
    headers = dict(DEFAULT_HEADERS)
    t = (token or "").strip()
    if t:
        headers["Authorization"] = f"Bearer {t}"
    return requests.request(method, url, headers=headers, params=params or {}, timeout=timeout)


def fetch_last_commit_audit_payload(
    owner: str,
    repo: str,
    branch: str = "main",
    token: Optional[str] = None,
    max_patch_per_file: int = 24_000,
    max_total_chars: int = 120_000,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Retourne (payload, erreur). Si erreur est non None, payload contient au minimum {"error": ...}.
    """
    err = _valid_owner_repo_branch(owner, repo, branch)
    if err:
        return {"error": err}, err

    o, r, b = owner.strip(), repo.strip(), (branch or "main").strip()
    try:
        r_list = _request("GET", f"/repos/{o}/{r}/commits", token, params={"sha": b, "per_page": 1})
        if r_list.status_code == 404:
            return {"error": "Dépôt ou branche introuvable (404). Vérifiez owner/repo/branche et les droits (token pour un dépôt privé)."}, "404"
        if r_list.status_code == 403:
            return {
                "error": "Accès refusé (403). Dépôt privé sans token, ou limite de taux GitHub — ajoutez GITHUB_TOKEN ou réessayez plus tard."
            }, "403"
        r_list.raise_for_status()
        commits = r_list.json()
        if not isinstance(commits, list) or not commits:
            return {"error": "Aucun commit sur cette branche."}, "empty"

        sha = commits[0].get("sha")
        if not sha:
            return {"error": "Réponse GitHub inattendue (pas de sha)."}, "parse"

        r_commit = _request("GET", f"/repos/{o}/{r}/commits/{sha}", token)
        if not r_commit.ok:
            return {"error": f"Impossible de lire le commit ({r_commit.status_code})."}, str(r_commit.status_code)
        data = r_commit.json()
        commit_info = data.get("commit") or {}
        meta = {
            "sha": sha,
            "short_sha": sha[:7],
            "message": (commit_info.get("message") or "")[:2000],
            "author": (commit_info.get("author") or {}).get("name"),
            "date": (commit_info.get("author") or {}).get("date"),
            "html_url": data.get("html_url"),
            "branch": b,
            "repository": f"{o}/{r}",
        }

        files: List[Dict[str, Any]] = data.get("files") or []
        out_files: List[Dict[str, Any]] = []
        total = 0
        truncated_global = False

        for f in files:
            name = f.get("filename") or ""
            status = f.get("status")
            additions = f.get("additions")
            deletions = f.get("deletions")
            patch = f.get("patch")
            entry: Dict[str, Any] = {
                "filename": name,
                "status": status,
                "additions": additions,
                "deletions": deletions,
            }
            if patch:
                if len(patch) > max_patch_per_file:
                    entry["patch"] = patch[:max_patch_per_file] + "\n\n[… patch tronqué …]"
                    entry["patch_truncated"] = True
                else:
                    entry["patch"] = patch
            else:
                entry["patch"] = None
                entry["note"] = "Pas de patch (fichier trop volumineux ou binaire) — considérer une revue manuelle sur GitHub."

            chunk = json.dumps(entry, ensure_ascii=False)
            if total + len(chunk) > max_total_chars:
                truncated_global = True
                break
            total += len(chunk)
            out_files.append(entry)

        payload: Dict[str, Any] = {
            "commit": meta,
            "files": out_files,
            "files_total_reported_by_github": len(files),
            "files_included": len(out_files),
        }
        if truncated_global:
            payload["warning"] = (
                "Volume limite atteint : certains fichiers modifiés ne sont pas inclus. "
                "Affinez la revue sur GitHub ou traitez un commit plus petit."
            )
        return payload, None
    except requests.RequestException as e:
        logger.warning("[github_last_commit] HTTP error: %s", e)
        return {"error": f"Erreur réseau ou API GitHub : {e}"}, "network"


def format_payload_for_llm(payload: Dict[str, Any]) -> str:
    """Sérialise le payload pour le contexte LLM (outil / agent)."""
    return json.dumps(payload, indent=2, ensure_ascii=False)
