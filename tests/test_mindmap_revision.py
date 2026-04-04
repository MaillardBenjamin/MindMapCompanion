"""Tests du compteur de révision mindmap (sync front / jobs arrière-plan)."""

from app.services import mindmap_revision as mr


def test_get_returns_zero_initially():
    assert mr.get_mindmap_revision(999001) == 0


def test_bump_increments_and_get_matches():
    mid = 999002
    assert mr.bump_mindmap_revision(mid) == 1
    assert mr.get_mindmap_revision(mid) == 1
    assert mr.bump_mindmap_revision(mid) == 2
    assert mr.get_mindmap_revision(mid) == 2


def test_mindmaps_are_independent():
    a, b = 999003, 999004
    mr.bump_mindmap_revision(a)
    mr.bump_mindmap_revision(a)
    mr.bump_mindmap_revision(b)
    assert mr.get_mindmap_revision(a) == 2
    assert mr.get_mindmap_revision(b) == 1
