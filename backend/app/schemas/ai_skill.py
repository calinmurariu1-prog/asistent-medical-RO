"""AI skill schemas."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class SkillOut(BaseModel):
    name: str
    title: str
    description: str
    inputs: list[str]


class SkillRunRequest(BaseModel):
    inputs: dict[Annotated[str, Field(max_length=64)], Annotated[str, Field(max_length=12000)]] = (
        Field(default_factory=dict, max_length=8)
    )


class SkillSource(BaseModel):
    ref: str
    title: str
    url: str | None = None
    kind: str = "public_guidance"
    checked_on: str | None = None


class SkillRunResponse(BaseModel):
    emergency: bool = False
    skill: str
    result: str
    sources: list[SkillSource] = Field(default_factory=list)
    abstained: bool | None = None
    simulated: bool | None = None
