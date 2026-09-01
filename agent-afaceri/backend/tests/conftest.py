"""Configurare teste: bază de date SQLite temporară, izolată."""
from __future__ import annotations

import os
import tempfile

# Setează mediul ÎNAINTE de importul aplicației (db.py citește la import).
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.db import init_db  # noqa: E402

init_db()
