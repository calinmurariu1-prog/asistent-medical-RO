"""AI skills — discrete medical AI capabilities (informational only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, require_ai_consent
from app.models.user import User
from app.schemas.ai_skill import SkillOut, SkillRunRequest, SkillRunResponse
from app.services.ai import get_ai_provider
from app.services.ai import skills as skills_service
from app.services.ai.base import AIProvider

router = APIRouter(prefix="/ai/skills", tags=["ai-skills"])


@router.get("", response_model=list[SkillOut])
def list_skills(_: User = Depends(get_current_user)) -> list[SkillOut]:
    return [
        SkillOut(
            name=s.name, title=s.title, description=s.description, inputs=s.inputs
        )
        for s in skills_service.list_skills()
    ]


@router.post(
    "/{name}",
    response_model=SkillRunResponse,
    dependencies=[Depends(require_ai_consent)],
)
def run_skill(
    name: str,
    payload: SkillRunRequest,
    _: User = Depends(get_current_user),
    ai: AIProvider = Depends(get_ai_provider),
) -> SkillRunResponse:
    skill = skills_service.get_skill(name)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill inexistent")

    missing = [
        key for key in skill.inputs if not (payload.inputs.get(key) or "").strip()
    ]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Câmpuri obligatorii lipsă: {', '.join(missing)}",
        )

    result = skills_service.run_skill(ai, skill, payload.inputs)
    return SkillRunResponse(skill=name, result=result)
