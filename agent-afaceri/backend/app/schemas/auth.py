"""Scheme pentru autentificare și documente."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = "general"
    content: str = Field(min_length=1)


class DocumentOut(BaseModel):
    id: int
    title: str
    category: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: int
    title: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    title: str = "Document"
    content: str = Field(min_length=1)
    format: str = "pdf"  # "pdf" | "docx"
