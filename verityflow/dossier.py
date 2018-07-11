"""Evidence dossier assembly and rendering.

A *dossier* is the human-facing deliverable: for each claim it lays out the
support verdict, the diversity of provenance, and the full chain of quotations
and sources that underpin (or contest) the claim. Dossiers render to Markdown
for review and to JSON for downstream tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .graph import compute_stats
from .model import ProvenanceGraph
from .scoring import ClaimScore, ScoreReport, score_graph


def _verdict(score: ClaimScore) -> str:
    if score.contested and not score.covered:
        return "refuted"
    if score.contested and score.covered:
        return "contested"
    if not score.covered:
        return "unsupported"
    if score.support_index >= 0.8 and score.n_domains >= 2:
        return "well-supported"
    if score.support_index >= 0.6:
        return "supported"
    return "weakly-supported"


@dataclass
class DossierEntry:
    claim_id: str
    claim_text: str
    topic: str
    verdict: str
    support_index: float
