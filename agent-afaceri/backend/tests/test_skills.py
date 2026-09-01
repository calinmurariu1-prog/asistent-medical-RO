"""Teste pentru registrul de skill-uri (mod offline determinist)."""
from __future__ import annotations

from app.services.ai import skills as skills_mod
from app.services.ai.mock import MockProvider


def test_registry_has_all_categories():
    names = {s.name for s in skills_mod.list_skills()}
    assert {
        "draft_contract",
        "analyze_contract",
        "company_setup",
        "tax_obligations",
        "business_plan",
        "swot_analysis",
    } <= names


def test_get_skill_unknown():
    assert skills_mod.get_skill("nope") is None


def test_run_skill_mock_draft_contract():
    skill = skills_mod.get_skill("draft_contract")
    out = skills_mod.run_skill(
        MockProvider(),
        skill,
        {"type": "prestări servicii", "parties": "SC A SRL și SC B SRL", "terms": "1000 lei/lună"},
    )
    assert "prestări servicii".upper() in out.upper()
    assert "orientativ" in out.lower()  # disclaimer atașat


def test_run_skill_mock_swot():
    skill = skills_mod.get_skill("swot_analysis")
    out = skills_mod.run_skill(MockProvider(), skill, {"business": "cafenea"})
    assert "SWOT" in out
    assert "cafenea" in out
