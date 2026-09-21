"""AI skills — discrete medical AI capabilities (informational only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, get_current_user, require_ai_consent
from app.core.config import settings
from app.core.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.ai_skill import SkillOut, SkillRunRequest, SkillRunResponse
from app.services.ai import get_ai_provider, record_ai
from app.services.ai import skills as skills_service
from app.services.ai.base import AIProvider

router = APIRouter(prefix="/ai", tags=["ai-skills"])


class AiTextResponse(BaseModel):
    result: str


class CompareRequest(BaseModel):
    analyte: str


class AIStatus(BaseModel):
    provider: str
    simulated: bool
    consent_required: bool


@router.get("/status", response_model=AIStatus)
def ai_status(_: User = Depends(get_current_user), ai: AIProvider = Depends(get_ai_provider)):
    return AIStatus(provider=ai.name, simulated=ai.name == "mock",
                    consent_required=settings.REQUIRE_AI_CONSENT or ai.name != "mock")


@router.get("/skills", response_model=list[SkillOut])
def list_skills(_: User = Depends(get_current_user)) -> list[SkillOut]:
    return [
        SkillOut(
            name=s.name, title=s.title, description=s.description, inputs=s.inputs
        )
        for s in skills_service.list_skills()
    ]


@router.post(
    "/skills/{name}",
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


@router.post(
    "/summarize-record",
    response_model=AiTextResponse,
    dependencies=[Depends(require_ai_consent)],
)
def summarize_record(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> AiTextResponse:
    """AI summary of the patient's whole record."""
    return AiTextResponse(result=record_ai.summarize_record(db, ai, patient))


@router.post(
    "/compare-analyte",
    response_model=AiTextResponse,
    dependencies=[Depends(require_ai_consent)],
)
def compare_analyte(
    payload: CompareRequest,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> AiTextResponse:
    """AI interpretation of how one analyte evolved over time."""
    return AiTextResponse(
        result=record_ai.compare_analyte(db, ai, patient, payload.analyte)
    )
