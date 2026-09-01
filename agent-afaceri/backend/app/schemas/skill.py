"""Scheme pentru skill-uri."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SkillOut(BaseModel):
    name: str
    title: str
    description: str
    category: str
    inputs: list[str]


class SkillRunRequest(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)


class SkillRunResponse(BaseModel):
    skill: str
    result: str
