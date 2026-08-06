"""Retrieval-augmented generation over the patient's own record (Module 11)."""
from app.services.rag.retriever import RetrievedContext, build_context

__all__ = ["RetrievedContext", "build_context"]
