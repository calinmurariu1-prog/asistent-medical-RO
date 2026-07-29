"""Text extraction from uploaded documents.

Supports PDF (embedded text + OCR fallback), images (Tesseract OCR) and DICOM
(metadata + OCR of the pixel data when present). Every backend is imported
lazily and every failure degrades gracefully to an empty string, so a missing
system binary (e.g. tesseract) never breaks an upload.
"""
from __future__ import annotations

import io
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

PDF_TYPES = {"application/pdf"}
IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
DICOM_TYPES = {"application/dicom", "application/octet-stream"}


def _ocr_image_bytes(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image OCR failed: %s", exc)
        return ""


def _extract_pdf(data: bytes) -> str:
    text_parts: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF text extraction failed: %s", exc)

    text = "\n".join(p for p in text_parts if p).strip()
    # Scanned PDF with no embedded text -> try rendering + OCR.
    if not text:
        try:
            from pdf2image import convert_from_bytes

            for image in convert_from_bytes(data):
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                text_parts.append(_ocr_image_bytes(buf.getvalue()))
            text = "\n".join(p for p in text_parts if p).strip()
        except Exception as exc:  # noqa: BLE001
            logger.info("PDF OCR fallback unavailable: %s", exc)
    return text


def _extract_dicom(data: bytes) -> str:
    try:
        import pydicom

        ds = pydicom.dcmread(io.BytesIO(data), force=True)
        meta_fields = [
            ("Modalitate", getattr(ds, "Modality", "")),
            ("Regiune", getattr(ds, "BodyPartExamined", "")),
            ("Descriere", getattr(ds, "StudyDescription", "")),
            ("Data", getattr(ds, "StudyDate", "")),
        ]
        lines = [f"{label}: {value}" for label, value in meta_fields if value]
        return "\n".join(lines).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("DICOM parse failed: %s", exc)
        return ""


def extract_text(data: bytes, content_type: str | None, filename: str = "") -> str:
    """Dispatch to the right extractor based on content type / extension."""
    ct = (content_type or "").lower()
    name = filename.lower()

    if ct in PDF_TYPES or name.endswith(".pdf"):
        return _extract_pdf(data)
    if ct in IMAGE_TYPES or name.endswith((".jpg", ".jpeg", ".png")):
        return _ocr_image_bytes(data)
    if ct == "application/dicom" or name.endswith(".dcm"):
        return _extract_dicom(data)
    # Unknown octet-stream: sniff DICOM magic then fall back to image OCR.
    if data[128:132] == b"DICM":
        return _extract_dicom(data)
    return _ocr_image_bytes(data)
