"""Abstracția providerului AI pentru agentul de afaceri & juridic.

Toate răspunsurile sunt informative. Nu constituie consultanță juridică,
fiscală sau contabilă profesională — pentru decizii se recomandă un
avocat / contabil / expert autorizat.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

DISCLAIMER = (
    "⚖️ Informațiile au caracter pur orientativ și NU constituie consultanță "
    "juridică, fiscală sau contabilă profesională. Pentru decizii concrete "
    "consultă un avocat, un contabil autorizat sau autoritatea competentă."
)


class AIProvider(ABC):
    """Interfață minimă pe care o implementează orice provider AI."""

    name: str = "base"

    @abstractmethod
    def complete(self, *, system: str, user: str) -> str:
        """Returnează un răspuns text pentru perechea (system, user)."""
        raise NotImplementedError
