"""
Compteur de révision par mindmap (mémoire process, thread-safe).

Utilisé pour que le front puisse poller et recharger le graphe après des
modifications faites en arrière-plan (ex. exécution d'un trigger cron).

Limite : en déploiement multi-workers, chaque processus a son propre compteur ;
le client peut néanmoins voir une hausse dès qu'il interroge le worker qui a
traité le job.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_revisions: dict[int, int] = {}


def bump_mindmap_revision(mindmap_id: int) -> int:
    """Incrémente la révision pour ce mindmap et retourne la nouvelle valeur."""
    with _lock:
        _revisions[mindmap_id] = _revisions.get(mindmap_id, 0) + 1
        return _revisions[mindmap_id]


def get_mindmap_revision(mindmap_id: int) -> int:
    """Retourne la révision actuelle (0 si jamais bump)."""
    with _lock:
        return _revisions.get(mindmap_id, 0)
