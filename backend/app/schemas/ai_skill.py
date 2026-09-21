"""AI skill schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SkillOut(BaseModel):
    name: str
    title: str
    description: str
    inputs: list[str]


class SkillRunRequest(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)


class SkillSource(BaseModel):
    ref: str
    title: str
    url: str
    checked_on: str | None = None


class SkillRunResponse(BaseModel):
    emergency: bool = False
    skill: str
    result: str
    sources: list[SkillSource] = Field(default_factory=list)
    abstained: bool | None = None
    simulated: bool | None = None
