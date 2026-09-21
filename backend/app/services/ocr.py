"""Extract embedded PDF/DOCX text and optionally OCR images or scans.

Unavailable OCR returns no text; the pipeline records an explicit failed state.
DOCX archives are bounded and checked before their contents are parsed.
"""
from __future__ import annotations

import io
import logging
import zipfile

from app.core.config import settings

logger = logging.getLogger(__name__)
# pypdf may include bytes from malformed inputs in diagnostic messages. Keep
# our sanitized exception-type diagnostics; never propagate raw parser output.
_pdf_logger = logging.getLogger("pypdf")
_pdf_logger.addHandler(logging.NullHandler())
_pdf_logger.propagate = False

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

PDF_TYPES = {"application/pdf"}
IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
DICOM_TYPES = {"application/dicom", "application/octet-stream"}


def validate_docx(data: bytes) -> None:
    """Bound the OOXML archive before loading its XML; never extract files to disk."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise ValueError("Fișier DOCX invalid.")
            if len(entries) > 2000 or sum(e.file_size for e in entries) > 25 * 1024 * 1024:
                raise ValueError("Documentul DOCX depășește limita de conținut decomprimat.")
            if any(e.flag_bits & 1 or e.file_size > max(e.compress_size, 1) * 200
                   for e in entries):
                raise ValueError("Arhivă DOCX criptată sau cu expansiune excesivă.")
            for entry in entries:
                if entry.filename.endswith(".xml"):
                    xml = archive.read(entry).upper()
                    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                        raise ValueError("Declarații XML neacceptate în DOCX.")
    except zipfile.BadZipFile:
        raise ValueError("Fișier DOCX invalid.") from None


def _extract_docx(data: bytes) -> str:
    from docx import Document as WordDocument
    from docx.table import Table

    validate_docx(data)
    document = WordDocument(io.BytesIO(data))
    lines = []
    for item in document.iter_inner_content():
        if isinstance(item, Table):
            lines.extend(" ".join(cell.text for cell in row.cells) for row in item.rows)
        else:
            lines.append(item.text)
    return "\n".join(lines).strip()


def _ocr_image_bytes(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image OCR failed (%s)", type(exc).__name__)
        return ""


def _extract_pdf(data: bytes) -> str:
    text_parts: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF text extraction failed (%s)", type(exc).__name__)

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
            logger.info("PDF OCR fallback unavailable (%s)", type(exc).__name__)
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
        logger.warning("DICOM parse failed (%s)", type(exc).__name__)
        return ""


def extract_text(data: bytes, content_type: str | None, filename: str = "") -> str:
    """Dispatch to the right extractor based on content type / extension."""
    ct = (content_type or "").lower()
    name = filename.lower()

    if ct == DOCX_TYPE or name.endswith(".docx"):
        return _extract_docx(data)
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
