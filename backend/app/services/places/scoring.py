"""Quality score (0-100%) for a provider.

Transparent heuristic: the rating (0-5) scaled to a percentage, weighted by a
confidence factor that grows with the number of reviews — a 4.9 from 500
reviews is more trustworthy than a 5.0 from 2. This is a convenience ranking
aid, NOT a medical endorsement.
"""
from __future__ import annotations

from math import log1p

# Reviews at/above this count count as "fully trusted".
_REVIEW_SATURATION = 300


def quality(rating: float | None, ratings_total: int | None) -> tuple[int | None, str]:
    if rating is None:
        return None, "Fără evaluări"
    reviews = ratings_total or 0
    confidence = min(1.0, log1p(reviews) / log1p(_REVIEW_SATURATION))
    score = round(100 * (rating / 5) * (0.7 + 0.3 * confidence))
    score = max(0, min(100, score))
    if score >= 85:
        label = "Excelent"
    elif score >= 70:
        label = "Foarte bun"
    elif score >= 55:
        label = "Bun"
    else:
        label = "Acceptabil"
    return score, label
