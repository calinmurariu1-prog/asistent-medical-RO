"""Rute pentru listarea și rularea skill-urilor."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.skill import SkillOut, SkillRunRequest, SkillRunResponse
from app.services.ai import skills as skills_mod
from app.services.ai.factory import get_provider

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def list_skills() -> list[SkillOut]:
    return [
        SkillOut(
            name=s.name,
            title=s.title,
            description=s.description,
            category=s.category,
            inputs=s.inputs,
        )
        for s in skills_mod.list_skills()
    ]


@router.post("/{name}/run", response_model=SkillRunResponse)
def run_skill(name: str, req: SkillRunRequest) -> SkillRunResponse:
    skill = skills_mod.get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill inexistent")
    missing = [i for i in skill.inputs if not req.inputs.get(i)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Lipsesc câmpuri obligatorii: {', '.join(missing)}",
        )
    result = skills_mod.run_skill(get_provider(), skill, req.inputs)
    return SkillRunResponse(skill=name, result=result)
