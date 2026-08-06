"""Module 13 - full medical report export (PDF / Word).

`gather_report_data` builds a plain dict; `render_pdf` and `render_docx` turn it
into bytes. reportlab / python-docx are imported lazily so importing this module
never requires them (e.g. in unrelated tests).
"""
from __future__ import annotations

import io
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical import MedicalHistory
from app.models.medication import Medication
from app.models.patient import Patient
from app.models.user import User
from app.services import lab_analysis, recommendations
from app.services.ai.base import DISCLAIMER

_TITLE = "Raport Medical - Asistent Medical AI"


def gather_report_data(db: Session, patient: Patient, user: User) -> dict:
    bmi = None
    if patient.weight_kg and patient.height_cm:
        h = patient.height_cm / 100
        bmi = round(patient.weight_kg / (h * h), 1)

    history = db.scalars(
        select(MedicalHistory)
        .where(MedicalHistory.patient_id == patient.id)
        .order_by(MedicalHistory.event_date.desc().nullslast())
    ).all()

    meds = db.scalars(
        select(Medication).where(
            Medication.patient_id == patient.id, Medication.is_active.is_(True)
        )
    ).all()

    lab_summary = lab_analysis.build_summary(db, patient.id)
    rec = recommendations.build_recommendations(db, patient)

    full_name = " ".join(
        p for p in [patient.first_name, patient.last_name] if p
    ) or (user.full_name or user.email)

    return {
        "generated_at": datetime.now(UTC).strftime("%d.%m.%Y %H:%M"),
        "patient": {
            "name": full_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else "-",
            "sex": patient.sex.value if patient.sex else "-",
            "blood_type": patient.blood_type.value if patient.blood_type else "-",
            "weight_kg": patient.weight_kg,
            "height_cm": patient.height_cm,
            "bmi": bmi,
        },
        "history": [
            {
                "date": h.event_date.isoformat() if h.event_date else "-",
                "type": h.event_type.value,
                "title": h.title,
            }
            for h in history
        ],
        "labs": [
            {
                "analyte": it["analyte"],
                "value": it["latest_value"],
                "unit": it["unit"] or "",
                "flag": it["flag"],
            }
            for it in lab_summary["items"]
        ],
        "medications": [
            {"name": m.name, "dose": m.dose or "", "frequency": m.frequency or ""}
            for m in meds
        ],
        "recommendations": {
            "alerts": rec.alerts,
            "questions_for_doctor": rec.questions_for_doctor,
        },
    }


def render_pdf(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=_TITLE)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(_TITLE, styles["Title"]))
    story.append(Paragraph(f"Generat: {data['generated_at']}", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))

    p = data["patient"]
    story.append(Paragraph("Pacient", styles["Heading2"]))
    story.append(Paragraph(f"Nume: {p['name']}", styles["Normal"]))
    story.append(
        Paragraph(
            f"Naștere: {p['birth_date']} | Sex: {p['sex']} | Grup sanguin: "
            f"{p['blood_type']} | IMC: {p['bmi'] or '-'}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    def _table(title: str, header: list[str], rows: list[list], empty: str) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        if not rows:
            story.append(Paragraph(empty, styles["Italic"]))
            story.append(Spacer(1, 0.3 * cm))
            return
        table = Table([header, *rows], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.3 * cm))

    _table(
        "Istoric medical",
        ["Data", "Tip", "Descriere"],
        [[h["date"], h["type"], h["title"]] for h in data["history"]],
        "Fără intrări.",
    )
    _table(
        "Analize (ultimele valori)",
        ["Analit", "Valoare", "Unitate", "Status"],
        [[lr["analyte"], lr["value"], lr["unit"], lr["flag"]] for lr in data["labs"]],
        "Fără analize.",
    )
    _table(
        "Tratamente active",
        ["Medicament", "Doză", "Frecvență"],
        [[m["name"], m["dose"], m["frequency"]] for m in data["medications"]],
        "Fără tratamente active.",
    )

    rec = data["recommendations"]
    story.append(Paragraph("Recomandări (orientative)", styles["Heading2"]))
    for line in rec["alerts"] + rec["questions_for_doctor"]:
        story.append(Paragraph(f"• {line}", styles["Normal"]))
    if not (rec["alerts"] or rec["questions_for_doctor"]):
        story.append(Paragraph("Fără recomandări.", styles["Italic"]))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(DISCLAIMER, styles["Italic"]))

    doc.build(story)
    return buf.getvalue()


def render_docx(data: dict) -> bytes:
    from docx import Document as Docx

    document = Docx()
    document.add_heading(_TITLE, level=0)
    document.add_paragraph(f"Generat: {data['generated_at']}")

    p = data["patient"]
    document.add_heading("Pacient", level=1)
    document.add_paragraph(f"Nume: {p['name']}")
    document.add_paragraph(
        f"Naștere: {p['birth_date']} | Sex: {p['sex']} | "
        f"Grup sanguin: {p['blood_type']} | IMC: {p['bmi'] or '-'}"
    )

    def _table(title: str, header: list[str], rows: list[list], empty: str) -> None:
        document.add_heading(title, level=1)
        if not rows:
            document.add_paragraph(empty)
            return
        table = document.add_table(rows=1, cols=len(header))
        table.style = "Light Grid Accent 1"
        for i, col in enumerate(header):
            table.rows[0].cells[i].text = col
        for row in rows:
            cells = table.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = str(val)

    _table(
        "Istoric medical",
        ["Data", "Tip", "Descriere"],
        [[h["date"], h["type"], h["title"]] for h in data["history"]],
        "Fără intrări.",
    )
    _table(
        "Analize (ultimele valori)",
        ["Analit", "Valoare", "Unitate", "Status"],
        [[lr["analyte"], lr["value"], lr["unit"], lr["flag"]] for lr in data["labs"]],
        "Fără analize.",
    )
    _table(
        "Tratamente active",
        ["Medicament", "Doză", "Frecvență"],
        [[m["name"], m["dose"], m["frequency"]] for m in data["medications"]],
        "Fără tratamente active.",
    )

    rec = data["recommendations"]
    document.add_heading("Recomandări (orientative)", level=1)
    lines = rec["alerts"] + rec["questions_for_doctor"]
    for line in lines:
        document.add_paragraph(line, style="List Bullet")
    if not lines:
        document.add_paragraph("Fără recomandări.")

    document.add_paragraph()
    document.add_paragraph(DISCLAIMER)

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
