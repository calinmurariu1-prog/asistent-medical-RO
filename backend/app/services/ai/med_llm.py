"""MedLLM provider — delegates to the `med-llm` micro-service (z-ai CLI wrapper).

Flow:  FastAPI  ->  HTTP POST /complete  ->  Node.js (med-llm :3031)  ->  z-ai CLI

Implements the same structural interface as the other AI providers
(`extract_document`, `explain_lab_value`, `chat`). All guardrails are enforced
via the prompts: no diagnosis, no prescription, disclaimer + [S#] citations.

Adapted from the integration doc to this project's import paths, settings and
the real chat-history shape (a flat list of (role, content) turns).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import settings
from app.services.ai.base import (
    DISCLAIMER,
    DocumentExtraction,
    ExtractedLabValue,
)

logger = logging.getLogger(__name__)


@dataclass
class MedLLMProvider:
    name: str = "medllm"
    base_url: str = field(default_factory=lambda: settings.MED_LLM_URL)
    timeout: float = field(default_factory=lambda: settings.MED_LLM_TIMEOUT)

    # ------------------------------------------------------------------
    def health_check(self) -> bool:
        """Return True if the micro-service answers GET /health."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=2.0)
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    # ------------------------------------------------------------------
    def _complete(self, system: str, user: str) -> str:
        """Call the micro-service POST /complete; fall back to the disclaimer."""
        try:
            resp = httpx.post(
                f"{self.base_url}/complete",
                json={"system": system, "user": user},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "")
            if not text.strip():
                logger.warning("[medllm] empty response from micro-service")
                return DISCLAIMER
            return text
        except httpx.HTTPStatusError as exc:
            logger.error("[medllm] HTTP %s: %s", exc.response.status_code, exc.response.text[:200])
            return DISCLAIMER
        except httpx.RequestError as exc:
            logger.error("[medllm] micro-service connection error: %s", exc)
            return DISCLAIMER

    def complete(self, *, system: str, user: str) -> str:
        return self._complete(system, user)

    # ------------------------------------------------------------------
    def extract_document(self, text: str, category: str) -> DocumentExtraction:
        system_prompt = (
            "Ești un asistent medical AI specializat în extragerea informațiilor "
            "din documente medicale.\n"
            "REGULI STRICTE:\n"
            "1. Răspunde DOAR cu un obiect JSON valid, fără markdown, fără backticks.\n"
            "2. Nu inventa date care nu sunt în textul furnizat.\n"
            "3. Dacă o informație lipsește, lasă lista goală sau null.\n"
            '4. "summary" = rezumat în 2-3 propoziții.\n'
            '5. "diagnoses"/"treatments"/"medications" = liste de string-uri.\n'
            '6. "lab_values" = obiecte {analyte, value, value_text, unit, ref_low, ref_high}.\n'
            f"Categoria documentului: {category}\n"
            f"{DISCLAIMER}"
        )
        raw = self._complete(system_prompt, text)

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                ln for ln in cleaned.splitlines() if not ln.strip().startswith("```")
            )
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("[medllm] invalid JSON from extract_document")
            return DocumentExtraction(summary=raw[:500])

        lab_values = [
            ExtractedLabValue(
                analyte=lv.get("analyte", ""),
                value=lv.get("value"),
                value_text=lv.get("value_text"),
                unit=lv.get("unit"),
                ref_low=lv.get("ref_low"),
                ref_high=lv.get("ref_high"),
            )
            for lv in (data.get("lab_values") or [])
            if lv.get("analyte")
        ]
        return DocumentExtraction(
            summary=str(data.get("summary", "")),
            diagnoses=[str(d) for d in data.get("diagnoses", [])],
            treatments=[str(t) for t in data.get("treatments", [])],
            medications=[str(m) for m in data.get("medications", [])],
            lab_values=lab_values,
        )

    # ------------------------------------------------------------------
    def explain_lab_value(
        self,
        *,
        analyte: str,
        value: float | None,
        unit: str | None,
        ref_low: float | None,
        ref_high: float | None,
        flag: str,
        trend: str | None = None,
    ) -> str:
        unit_str = unit or ""
        ref_str = (
            f"{ref_low} – {ref_high}"
            if ref_low is not None and ref_high is not None
            else "? – ?"
        )
        user_prompt = (
            "Explică următoarea valoare de laborator în limbaj simplu, accesibil "
            "unui pacient:\n"
            f"- Analiză: {analyte}\n"
            f"- Valoare: {value if value is not None else 'N/A'} {unit_str}\n"
            f"- Referință normală: {ref_str} {unit_str}\n"
            f"- Flag: {flag}\n"
            f"- Trend: {trend or 'fără trend'}\n"
            "Răspunde în 3-5 propoziții (ce înseamnă, ce indică valoarea, posibile "
            "cauze, când să consulte medicul).\n"
            f"{DISCLAIMER}"
        )
        system = (
            "Ești un asistent medical care explică analize de laborator pacienților. "
            "Fii clar, empatic și concis. Nu pune diagnostic. Răspunde în română."
        )
        return self._complete(system, user_prompt)

    # ------------------------------------------------------------------
    def chat(
        self,
        *,
        question: str,
        context: str,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        system_prompt = (
            "Ești un asistent medical virtual profesionist și empatic.\n"
            "REGULI STRICTE:\n"
            "1. Răspunde DOAR din contextul furnizat plus cunoștințe generale.\n"
            "2. NU inventa informații — dacă lipsesc date, spune explicit.\n"
            "3. NU pune diagnostic definitiv și NU prescrie tratament.\n"
            "4. Citează sursele din context prin marcajele [S#].\n"
            "5. Răspunde în limba română și încheie cu disclaimer.\n"
            f"Context:\n{context or '(gol)'}\n"
            f"{DISCLAIMER}"
        )
        # `history` is a flat list of (role, content) turns.
        parts: list[str] = []
        for role, content in (history or [])[-6:]:
            label = "Pacient" if role == "user" else "Asistent"
            parts.append(f"{label}: {content}")
        parts.append(f"Pacient: {question}")
        return self._complete(system_prompt, "\n\n".join(parts))
