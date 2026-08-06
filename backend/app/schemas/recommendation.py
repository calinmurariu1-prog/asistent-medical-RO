"""Recommendation schemas (Module 7)."""
from __future__ import annotations

from pydantic import BaseModel


class RecommendationsOut(BaseModel):
    questions_for_doctor: list[str]
    investigations: list[str]
    lifestyle: list[str]
    monitoring: list[str]
    alerts: list[str]
    disclaimer: str
