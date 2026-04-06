"""
Vérification de disponibilité et scénario fonctionnel (Playwright) à partir d'instructions en langage naturel.

1. Contrôle HTTP rapide (GET).
2. Traduction des instructions en plan d'étapes JSON via le LLM (français / anglais).
3. Exécution Playwright (headless).
4. Optionnel : après échec, capture PNG de la page, régénération du plan par le LLM (souvent avec vision),
   jusqu'à SITE_HEALTH_MAX_REPAIRS fois, puis nouvelle exécution depuis le début.
5. En cas d'échec final : email d'alerte (SMTP via settings IMAP_*).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from agno.agent import Agent
from agno.media import Image

from app.core.agno_model import get_agno_chat_model
from app.core.config import get_settings
from app.services.email_smtp import send_email

logger = logging.getLogger(__name__)

# Logs détaillés Playwright : même logger, préfixe [SiteHealth][PW]


def _redact_step_for_log(step: Dict[str, Any]) -> Dict[str, Any]:
    """Copie d'une étape pour les logs : masque les valeurs saisies (mots de passe, etc.)."""
    out = {k: v for k, v in step.items()}
    if out.get("action") == "fill" and "value" in out:
        out["value"] = "[REDACTÉ]"
    return out


def sanitize_failure_meta_for_client(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Exclut les octets PNG du dict exposé (JSON outil / API) ; garde un indicateur de taille."""
    out = {k: v for k, v in meta.items() if k != "screenshot_png"}
    blob = meta.get("screenshot_png")
    if blob and isinstance(blob, (bytes, bytearray)):
        out["failure_screenshot_captured"] = True
        out["failure_screenshot_bytes"] = len(blob)
    return out


ALLOWED_ACTIONS = frozenset(
    {
        "goto",
        "click",
        "fill",
        "press",
        "wait_for_selector",
        "wait_for_timeout",
        "expect_visible",
        "expect_title_contains",
    }
)

PLANNER_INSTRUCTIONS = """Tu es un ingénieur QA qui produit des plans de test Playwright en JSON.

Tu dois répondre UNIQUEMENT par un tableau JSON (array) d'objets, sans markdown, sans texte avant ou après.

URL de départ déjà ouverte dans le navigateur : l'utilisateur commence sur cette page. N'inclus pas de goto vers cette URL exacte sauf si tu dois ouvrir une autre page.

Actions autorisées (clé "action" obligatoire) :
- {"action":"goto","url":"https://..."}  — navigation vers une autre URL complète
- {"action":"click","selector":"...","force":false}  — optional "force": true si un overlay / une modal intercepte le clic (pointer-events) ; à utiliser avec parcimonie
- {"action":"fill","selector":"...","value":"..."}
- {"action":"fill","role":"textbox","name":"exemple@email.com","value":"..."}  — équivalent getByRole('textbox', { name: '…' }) ; préférable sur login MUI si tu connais le nom accessible du champ
- {"action":"press","key":"Enter"}
- {"action":"wait_for_selector","selector":"...","timeout_ms":15000}
- {"action":"wait_for_selector","role":"link","has_text":"Déconnexion"}  — getByRole+filter (sans selector) ; ou "name":"…" pour le nom accessible exact
- {"action":"click","role":"button","name":"Accepter tout"}  — équivalent getByRole('button', { name: 'Accepter tout' }) ; utile bannières cookies / consentement
- {"action":"click","role":"button","name":"Se connecter"}  — CTA « Se connecter » en AppBar : souvent un Button MUI (pas un lien). Ne pas utiliser role "link" pour ce libellé sauf preuve d’un vrai <a href>.
- {"action":"wait_for_timeout","ms":500}
- {"action":"expect_visible","selector":"...","timeout_ms":15000}
- {"action":"expect_title_contains","substring":"..."}

Règles :
- Préfère data-testid, #id, ou text= libellé visible.
- Menus MUI / listes : si text= matche un span mais l’élément cliquable est un lien, utiliser role + has_text ou role + name plutôt que selector text=.
- Cohérence des rôles : pour chaque clic via role+name, aligne-toi sur ce que produirait `playwright codegen` (ex. « Se connecter » en tête de page = quasi toujours `role: "button"`). Si `text=…` trouve l’élément mais `get_by_role("link", name=…)` timeoute, le bon rôle est souvent `button`.
- Soumission formulaire : le nom accessible du bouton peut être « Connexion », « Connection » ou autre — utiliser la chaîne exacte du site (comme dans le codegen), sans la « corriger ».
- Boutons « Tout accepter » / « Accepter tout » (RGPD) : préférer {"action":"click","role":"button","name":"…"} avec le libellé accessible exact plutôt que text=.
- Étapes courtes et robustes ; timeouts raisonnables (souvent 15000 ms pour wait).
- Si les instructions demandent de « vérifier que X est visible », utilise expect_visible sur un élément concret (champ email, bouton submit), pas sur le seul sélecteur « form » : sur beaucoup de SPA/MUI il n’y a pas de <form> exposé comme visible au sens Playwright alors que les champs le sont — après une page login, attend plutôt `input[type="email"]`, `input[type="password"]`, ou `role: "textbox"` + `name` (comme dans playwright codegen).
- Si un bouton est visible mais qu'un overlay bloque le clic (comme en prod avec MUI), essaie "force": true sur ce click uniquement.
- Instructions du type « cliquer sur X si présent / si le lien existe » : le JSON n’a pas d’étape optionnelle — ne pas dupliquer X **après chaque navigation**. Ex. « Mettre à jour » sur la home puis « Se connecter » mène à `/login` où « Mettre à jour » n’existe souvent plus : **ne pas** refaire wait_for_selector + click sur X sur la page login (ça timeout). Au plus une passe « X si visible » sur la page d’accueil avant le login ; après login, enchaîne sur les champs (email / password / bouton connexion).
"""

REPAIR_SUPPLEMENT = """### Mode réparation
Si le message utilisateur commence par « CONTEXTE ÉCHEC PLAYWRIGHT », un plan JSON a échoué pendant l'exécution réelle.
Tu dois répondre **UNIQUEMENT** par un **nouveau** tableau JSON d'étapes **complet** (tout le scénario depuis le chargement initial sur l'URL de départ — même format et mêmes règles que ci-dessus), qui corrige la cause de l'échec tout en respectant les instructions utilisateur d'origine.

Pistes de correction :
- **Timeout / introuvable** : remplacer `text=` fragiles par `role` + `name` ou `has_text` (équivalent getByRole), ou `force: true` si overlay.
- **Mauvais rôle** : « Se connecter » en AppBar → souvent `role: "button"` et non `link`.
- **Élément absent sur la page courante** (l'URL au moment de l'échec est indiquée) : retirer une étape qui ne s'applique qu'à une autre page (ex. bouton d'accueil après redirection login).
- **Champs login** : préférer `role: "textbox"` + `name` du placeholder si besoin.
- Si une **capture d'écran** de la page à l'échec est fournie en image, appuie-toi sur ce que tu vois (boutons, liens, champs visibles) pour corriger `role`, `name`, `has_text` ou `selector`.
"""


def _is_reasonable_url(url: str) -> bool:
    u = (url or "").strip()
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def quick_http_check(url: str, timeout_sec: float = 15.0) -> Tuple[bool, str]:
    """Retourne (ok, détail)."""
    logger.info("[SiteHealth][HTTP] GET %s timeout=%ss", url, timeout_sec)
    try:
        r = requests.get(
            url,
            timeout=timeout_sec,
            allow_redirects=True,
            headers={"User-Agent": "PersonalAssistant-SiteHealth/1.0"},
        )
        if r.status_code >= 500:
            logger.warning("[SiteHealth][HTTP] Échec serveur status=%s final_url=%s", r.status_code, r.url)
            return False, f"HTTP {r.status_code} (erreur serveur)"
        if r.status_code >= 400:
            logger.warning("[SiteHealth][HTTP] Erreur client status=%s final_url=%s", r.status_code, r.url)
            return False, f"HTTP {r.status_code}"
        logger.info(
            "[SiteHealth][HTTP] OK status=%s bytes=%s final_url=%s",
            r.status_code,
            len(r.content),
            r.url,
        )
        return True, f"HTTP {r.status_code}, {len(r.content)} octets"
    except requests.RequestException as e:
        logger.warning("[SiteHealth][HTTP] Exception: %s", e)
        return False, str(e)


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    text = (text or "").strip()
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        raise ValueError("Aucun tableau JSON trouvé dans la réponse du modèle")
    return json.loads(m.group(0))


def _step_has_locator_target(step: Dict[str, Any]) -> bool:
    """Cible via selector string OU get_by_role (name et/ou has_text)."""
    if step.get("selector"):
        return True
    role = (step.get("role") or "").strip()
    if not role:
        return False
    for key in ("name", "has_text"):
        v = step.get(key)
        if v is not None and str(v).strip() != "":
            return True
    return False


def _resolve_locator(page: Any, step: Dict[str, Any]) -> Any:
    """Construit un Locator Playwright : selector classique ou role+name/has_text."""
    role = (step.get("role") or "").strip()
    if role:
        name_raw, has_raw = step.get("name"), step.get("has_text")
        name = str(name_raw).strip() if name_raw is not None and str(name_raw).strip() else None
        has_text = str(has_raw).strip() if has_raw is not None and str(has_raw).strip() else None
        if not name and not has_text:
            raise ValueError("role nécessite name ou has_text non vide")
        if name and has_text:
            return page.get_by_role(role, name=name).filter(has_text=has_text)
        if name:
            return page.get_by_role(role, name=name)
        return page.get_by_role(role).filter(has_text=has_text)
    sel = step.get("selector")
    if not sel:
        raise ValueError("selector ou role+name/has_text requis")
    return page.locator(str(sel))


def validate_steps(steps: Any) -> Optional[str]:
    if not isinstance(steps, list):
        return "Le plan doit être une liste d'étapes"
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return f"Étape {i + 1} : objet attendu"
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            return f"Étape {i + 1} : action non autorisée ({action!r})"
        if action == "goto" and not step.get("url"):
            return f"Étape {i + 1} : goto requiert url"
        if action in ("click", "fill", "wait_for_selector", "expect_visible") and not _step_has_locator_target(step):
            return (
                f"Étape {i + 1} : {action} requiert selector ou role avec name ou has_text"
            )
        if action == "fill" and "value" not in step:
            return f"Étape {i + 1} : fill requiert value"
        if action == "press" and not step.get("key"):
            return f"Étape {i + 1} : press requiert key"
        if action == "expect_title_contains" and not step.get("substring"):
            return f"Étape {i + 1} : expect_title_contains requiert substring"
        if action == "wait_for_timeout":
            try:
                int(step.get("ms", 0))
            except (TypeError, ValueError):
                return f"Étape {i + 1} : wait_for_timeout requiert ms entier"
        if action == "click" and step.get("force") is not None:
            f = step["force"]
            if not isinstance(f, bool):
                return f"Étape {i + 1} : click.force doit être un booléen"
    return None


def nl_to_playwright_steps(url: str, user_instructions: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Appelle le LLM pour produire la liste d'étapes."""
    settings = get_settings()
    if getattr(settings, "skip_agent_llm", False):
        return None, "SKIP_AGENT_LLM est activé : impossible de traduire les instructions en plan Playwright."

    if not (user_instructions or "").strip():
        return [], None

    model = get_agno_chat_model()
    agent = Agent(
        model=model,
        name="SiteHealthPlanner",
        instructions=PLANNER_INSTRUCTIONS,
    )
    user_msg = (
        f"URL de départ (déjà chargée) : {url}\n\n"
        f"Instructions utilisateur à traduire en plan d'étapes Playwright :\n{user_instructions.strip()}\n\n"
        "Réponds uniquement avec le tableau JSON."
    )
    try:
        response = agent.run(user_msg)
        raw = getattr(response, "content", None) or str(response)
        steps = _extract_json_array(raw)
        err = validate_steps(steps)
        if err:
            return None, err
        logger.info("[SiteHealth][LLM] Plan généré: %d étape(s)", len(steps))
        logger.info(
            "[SiteHealth][LLM] Étapes (masquées): %s",
            json.dumps([_redact_step_for_log(s) for s in steps], ensure_ascii=False, indent=2),
        )
        return steps, None
    except Exception as e:
        logger.exception("[SiteHealth] Échec planification LLM: %s", e)
        return None, str(e)


def repair_playwright_steps_llm(
    url: str,
    user_instructions: str,
    failed_plan: List[Dict[str, Any]],
    failure_meta: Dict[str, Any],
    error_message: str,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Demande au LLM un plan JSON complet corrigé après échec Playwright (même schéma que la génération initiale).
    """
    settings = get_settings()
    if getattr(settings, "skip_agent_llm", False):
        return None, "SKIP_AGENT_LLM : réparation du plan impossible."
    if not failed_plan:
        return None, "Plan échoué vide, rien à analyser."

    model = get_agno_chat_model()
    agent = Agent(
        model=model,
        name="SiteHealthRepair",
        instructions=PLANNER_INSTRUCTIONS + "\n\n" + REPAIR_SUPPLEMENT,
    )
    plan_masked = [_redact_step_for_log(dict(s)) for s in failed_plan]
    usr = (
        "CONTEXTE ÉCHEC PLAYWRIGHT\n\n"
        f"URL de départ (navigateur chargé dessus au début) : {url}\n"
        f"Étape en échec : {failure_meta.get('failed_step_1based', '?')} / {len(failed_plan)} "
        f"(action: {failure_meta.get('failed_action', '?')})\n"
        f"URL page au moment de l'échec : {failure_meta.get('page_url', '')}\n"
        f"Titre page : {failure_meta.get('page_title', '')}\n"
        f"Erreur : {error_message}\n\n"
        "Plan ayant échoué (valeurs sensibles masquées) :\n"
        f"{json.dumps(plan_masked, indent=2, ensure_ascii=False)}\n\n"
        "Instructions utilisateur (respecter l'intention) :\n"
        f"{(user_instructions or '').strip()}\n\n"
    )
    screenshot_png: Optional[bytes] = None
    if isinstance(failure_meta, dict):
        raw = failure_meta.get("screenshot_png")
        if isinstance(raw, (bytes, bytearray)):
            screenshot_png = bytes(raw)
    use_vision = (
        bool(screenshot_png)
        and getattr(settings, "site_health_repair_with_screenshot", True)
    )
    if use_vision:
        usr += (
            "Une **capture d'écran PNG** de la page au moment de l'échec est jointe (image). "
            "Analyse ce qui est visible à l'écran pour corriger le plan (rôles ARIA, libellés, éléments absents).\n\n"
        )
    usr += "Réponds uniquement avec le nouveau tableau JSON complet d'étapes."
    try:
        images: Optional[List[Image]] = None
        if use_vision and screenshot_png is not None:
            images = [Image(content=screenshot_png, mime_type="image/png", detail="high")]
            logger.info(
                "[SiteHealth][LLM] Réparation avec capture (%d octets) pour le modèle vision",
                len(screenshot_png),
            )
        response = agent.run(usr, images=images)
        content_raw = getattr(response, "content", None) or str(response)
        steps = _extract_json_array(content_raw)
        err = validate_steps(steps)
        if err:
            logger.warning("[SiteHealth][LLM] Plan réparé invalide: %s", err)
            return None, err
        logger.info("[SiteHealth][LLM] Plan réparé: %d étape(s)", len(steps))
        logger.info(
            "[SiteHealth][LLM] Étapes réparées (masquées): %s",
            json.dumps([_redact_step_for_log(s) for s in steps], ensure_ascii=False, indent=2),
        )
        return steps, None
    except Exception as e:
        logger.exception("[SiteHealth] Échec réparation LLM: %s", e)
        return None, str(e)


async def execute_playwright_steps(
    start_url: str,
    steps: List[Dict[str, Any]],
    *,
    default_timeout_ms: int = 30_000,
    headless: bool = True,
) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
    from playwright.async_api import async_playwright

    logs: List[str] = []
    page = None
    browser = None
    context = None
    try:
        logger.info(
            "[SiteHealth][PW] Démarrage Chromium headless=%s default_timeout_ms=%s étapes_plan=%d url=%s",
            headless,
            default_timeout_ms,
            len(steps),
            start_url,
        )
        logger.info(
            "[SiteHealth][PW] Plan (valeurs sensibles masquées): %s",
            json.dumps([_redact_step_for_log(s) for s in steps], ensure_ascii=False, indent=2),
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(default_timeout_ms)

            async def _page_state_line() -> str:
                try:
                    t = await page.title()
                    return f"url={page.url!r} title={t!r}"
                except Exception as ex:
                    return f"(état page indisponible: {ex})"

            await page.goto(start_url, wait_until="domcontentloaded", timeout=default_timeout_ms)
            logs.append(f"goto {start_url} ok")
            logger.info(
                "[SiteHealth][PW] Navigation initiale OK (%s)",
                await _page_state_line(),
            )

            for i, step in enumerate(steps):
                action = step["action"]
                timeout = int(step.get("timeout_ms") or default_timeout_ms)
                step_no = f"{i + 1}/{len(steps)}"
                logger.info(
                    "[SiteHealth][PW] ─── Étape %s AVANT action=%s payload=%s | %s",
                    step_no,
                    action,
                    json.dumps(_redact_step_for_log(step), ensure_ascii=False),
                    await _page_state_line(),
                )

                try:
                    if action == "goto":
                        await page.goto(
                            step["url"],
                            wait_until="domcontentloaded",
                            timeout=default_timeout_ms,
                        )
                    elif action == "click":
                        force = bool(step.get("force", False))
                        loc = _resolve_locator(page, step)
                        await loc.first.click(timeout=timeout, force=force)
                    elif action == "fill":
                        loc = _resolve_locator(page, step)
                        await loc.first.fill(
                            str(step.get("value", "")),
                            timeout=timeout,
                        )
                    elif action == "press":
                        await page.keyboard.press(step["key"])
                    elif action == "wait_for_selector":
                        loc = _resolve_locator(page, step)
                        await loc.first.wait_for(state="visible", timeout=timeout)
                    elif action == "wait_for_timeout":
                        await page.wait_for_timeout(int(step["ms"]))
                    elif action == "expect_visible":
                        loc = _resolve_locator(page, step)
                        await loc.first.wait_for(state="visible", timeout=timeout)
                    elif action == "expect_title_contains":
                        await page.wait_for_function(
                            "(expected) => document.title.includes(expected)",
                            arg=step["substring"],
                            timeout=timeout,
                        )
                except Exception as e:
                    msg = f"{type(e).__name__}: {e}"
                    logs.append(f"step {i + 1} {action} FAIL: {msg}")
                    fail_meta: Dict[str, Any] = {
                        "failed_index": i,
                        "failed_step_1based": i + 1,
                        "failed_action": action,
                        "failed_step": _redact_step_for_log(dict(step)),
                        "page_url": "",
                        "page_title": "",
                    }
                    try:
                        if page is not None:
                            fail_meta["page_url"] = page.url
                            fail_meta["page_title"] = await page.title()
                    except Exception:
                        pass
                    if getattr(get_settings(), "site_health_failure_screenshot", True):
                        try:
                            if page is not None:
                                cap_to = min(10_000, int(default_timeout_ms))
                                png = await page.screenshot(
                                    type="png",
                                    full_page=False,
                                    timeout=cap_to,
                                )
                                fail_meta["screenshot_png"] = png
                                logs.append(
                                    f"step {i + 1} capture échec PNG ({len(png)} octets)"
                                )
                        except Exception as ss_err:
                            logger.warning(
                                "[SiteHealth][PW] Capture d'écran impossible à l'échec : %s",
                                ss_err,
                            )
                    logger.error(
                        "[SiteHealth][PW] Échec étape %s action=%s | %s | détail=%s",
                        step_no,
                        action,
                        await _page_state_line(),
                        msg,
                        exc_info=True,
                    )
                    if context is not None:
                        await context.close()
                    if browser is not None:
                        await browser.close()
                    return False, msg, logs, fail_meta

                line_ok = f"step {i + 1} {action} ok"
                logs.append(line_ok)
                logger.info(
                    "[SiteHealth][PW] Étape %s OK (%s)",
                    step_no,
                    await _page_state_line(),
                )

            await context.close()
            await browser.close()
        logger.info("[SiteHealth][PW] Scénario terminé avec succès (%d étapes exécutées)", len(steps))
        return True, "Scénario Playwright terminé avec succès", logs, None
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logs.append(f"fatal: {msg}")
        logger.error(
            "[SiteHealth][PW] Erreur fatale Playwright: %s | page=%s",
            msg,
            page.url if page else "(n/a)",
            exc_info=True,
        )
        try:
            if context is not None:
                await context.close()
            if browser is not None:
                await browser.close()
        except Exception:
            pass
        return False, msg, logs, None


def run_playwright_sync(
    start_url: str,
    steps: List[Dict[str, Any]],
    *,
    default_timeout_ms: int,
    headless: bool,
) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
    """
    Exécute Playwright de façon synchrone. Agno/arun tourne déjà dans une event loop :
    ``asyncio.run()`` y est interdit ; on isole alors l'exécution dans un thread avec sa propre boucle.
    Retourne ``failure_meta`` (étape, URL page, etc.) uniquement si le scénario échoue sur une étape.
    """

    def _run_isolated() -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        return asyncio.run(
            execute_playwright_steps(
                start_url,
                steps,
                default_timeout_ms=default_timeout_ms,
                headless=headless,
            )
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_isolated()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_run_isolated).result()


def send_failure_alert(
    to_email: str,
    site_url: str,
    phase: str,
    detail: str,
    plan: Optional[Union[List[Dict[str, Any]], str]] = None,
) -> bool:
    if not (to_email or "").strip():
        logger.warning("[SiteHealth] Pas d'alert_email, notification ignorée")
        return False
    settings = get_settings()
    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        logger.error("[SiteHealth] SMTP non configuré (IMAP_HOST / IMAP_USER / IMAP_PASSWORD)")
        return False

    subject = f"[MindMapCompanion] Site KO ou scénario en échec — {site_url}"
    body = (
        f"La vérification a échoué.\n\n"
        f"URL : {site_url}\n"
        f"Phase : {phase}\n"
        f"Détail : {detail}\n\n"
    )
    if plan is not None:
        if isinstance(plan, list):
            body += "Plan exécuté (JSON) :\n" + json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        else:
            body += f"Plan / contexte :\n{plan}\n"
    return send_email(to_email.strip(), subject, body, None)


def run_site_health_check(
    url: str,
    user_instructions: str,
    *,
    alert_email: str,
    steps_json_override: Optional[str] = None,
    default_timeout_ms: int = 30_000,
    headless: bool = True,
    http_timeout_sec: float = 15.0,
) -> Dict[str, Any]:
    """
    Orchestration complète : HTTP, plan LLM (ou override JSON), Playwright, alerte email si échec.
    """
    out: Dict[str, Any] = {
        "url": url,
        "http_ok": None,
        "playwright_ok": None,
        "alert_sent": False,
        "playwright_headless": headless,
    }

    if not _is_reasonable_url(url):
        out["error"] = "URL invalide (http/https requis)"
        if alert_email:
            out["alert_sent"] = send_failure_alert(alert_email, url, "validation", out["error"], None)
        return out

    http_ok, http_detail = quick_http_check(url, timeout_sec=http_timeout_sec)
    out["http_ok"] = http_ok
    out["http_detail"] = http_detail

    if not http_ok:
        out["error"] = f"Indisponible ou erreur HTTP : {http_detail}"
        if alert_email:
            out["alert_sent"] = send_failure_alert(alert_email, url, "HTTP", http_detail, user_instructions)
        return out

    steps: Optional[List[Dict[str, Any]]] = None
    plan_error: Optional[str] = None

    if steps_json_override and steps_json_override.strip():
        try:
            steps = json.loads(steps_json_override.strip())
        except json.JSONDecodeError as e:
            plan_error = f"steps_json invalide : {e}"
        if steps is not None:
            plan_error = validate_steps(steps)
            if plan_error:
                steps = None
    else:
        steps, plan_error = nl_to_playwright_steps(url, user_instructions)

    if plan_error:
        out["error"] = f"Plan : {plan_error}"
        if alert_email:
            out["alert_sent"] = send_failure_alert(
                alert_email, url, "planification_IA", plan_error, user_instructions
            )
        return out

    steps = steps or []
    out["steps"] = steps

    settings = get_settings()
    max_repairs = max(0, int(getattr(settings, "site_health_max_repairs", 0) or 0))
    all_logs: List[str] = []
    repairs_done = 0
    pw_msg = ""
    fail_meta: Optional[Dict[str, Any]] = None

    while True:
        logger.info(
            "[SiteHealth] Lancement Playwright: %d étape(s) pour %s (tour exécution=%s, réparations LLM déjà faites=%s)",
            len(steps),
            url,
            repairs_done + 1,
            repairs_done,
        )
        ok, pw_msg, logs, fail_meta = run_playwright_sync(
            url,
            steps,
            default_timeout_ms=default_timeout_ms,
            headless=headless,
        )
        prefix = f"[exécution {repairs_done + 1}] "
        all_logs.extend(f"{prefix}{line}" for line in logs)
        for line in logs:
            logger.info("[SiteHealth][PW][résumé] %s%s", prefix, line)

        if ok:
            out["playwright_ok"] = True
            out["playwright_message"] = pw_msg
            out["playwright_logs"] = all_logs
            out["playwright_repair_rounds"] = repairs_done
            return out

        can_repair = (
            max_repairs > 0
            and not getattr(settings, "skip_agent_llm", False)
            and fail_meta is not None
        )
        if not can_repair or repairs_done >= max_repairs:
            break

        new_steps, rerr = repair_playwright_steps_llm(
            url, user_instructions, steps, fail_meta, pw_msg
        )
        if rerr or not new_steps:
            out["playwright_repair_error"] = rerr or "plan réparé vide"
            break

        steps = new_steps
        out["steps"] = steps
        repairs_done += 1
        all_logs.append(
            f"[auto-correction LLM] Nouveau plan ({len(steps)} étapes), réparation {repairs_done}/{max_repairs}"
        )
        logger.info("[SiteHealth] Plan remplacé après auto-correction (%d étapes)", len(steps))

    out["playwright_ok"] = False
    out["playwright_message"] = pw_msg
    out["playwright_logs"] = all_logs
    out["playwright_repair_rounds"] = repairs_done
    out["error"] = pw_msg
    if fail_meta:
        out["playwright_failure_meta"] = sanitize_failure_meta_for_client(fail_meta)
    if out.get("playwright_repair_error"):
        out["error"] = f"{pw_msg} | Réparation : {out['playwright_repair_error']}"

    if alert_email:
        out["alert_sent"] = send_failure_alert(alert_email, url, "playwright", out["error"], steps)

    return out
