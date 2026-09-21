"""Bounded account archive; originals never touch a plaintext temporary file."""
import hashlib
import io
import json
from zipfile import ZIP_STORED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.patient import Patient
from app.models.user import User
from app.services.gdpr import export_user_data
from app.services.storage import Storage

MAX_BYTES = 25 * 1024 * 1024
MAX_DOCUMENTS = 1000


class ArchiveTooLarge(Exception):
    pass


def build(db: Session, user: User, storage: Storage) -> bytes:
    documents = list(db.scalars(select(Document).join(Patient).where(
        Patient.user_id == user.id).order_by(Document.id).limit(MAX_DOCUMENTS + 1)))
    if len(documents) > MAX_DOCUMENTS or sum(d.size_bytes or 0 for d in documents) > MAX_BYTES:
        raise ArchiveTooLarge()
    data = export_user_data(db, user)
    if {d["id"] for d in data.get("documents", [])} != {d.id for d in documents}:
        raise RuntimeError("Document list changed; retry export")
    data["export_metadata"]["original_files_included"] = True
    data["export_metadata"]["not_included"].remove("original_file_bytes")
    manifest = []
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for document in documents:
            content = storage.get(document.storage_key)
            if output.tell() + len(content) > MAX_BYTES:
                raise ArchiveTooLarge()
            # Never interpret original names as archive paths.
            suffix = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/jpg": "jpg",
                      "image/png": "png", "application/dicom": "dcm",
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                          "docx"}.get(document.content_type, "bin")
            path = f"originals/document-{document.id}.{suffix}"
            archive.writestr(path, content)
            manifest.append({"document_id": document.id, "path": path,
                             "original_filename": document.original_filename,
                             "content_type": document.content_type, "size_bytes": len(content),
                             "sha256": hashlib.sha256(content).hexdigest()})
        data["originals_manifest"] = manifest
        encoded = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if output.tell() + len(encoded) > MAX_BYTES:
            raise ArchiveTooLarge()
        archive.writestr("dosar.json", encoded)
    if output.tell() > MAX_BYTES:
        raise ArchiveTooLarge()
    return output.getvalue()
