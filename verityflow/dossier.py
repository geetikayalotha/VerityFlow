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
    diversity: float
    quotations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Dossier:
    title: str
    coverage: float
    mean_support: float
    mean_diversity: float
    stats: Dict[str, Any]
    entries: List[DossierEntry] = field(default_factory=list)


def build_dossier(graph: ProvenanceGraph, title: str = "Evidence Dossier") -> Dossier:
    """Assemble a :class:`Dossier` from a compiled *graph*."""
    report: ScoreReport = score_graph(graph)
    score_by_claim = {c.claim_id: c for c in report.claims}

    entries: List[DossierEntry] = []
    for cid, claim in graph.claims.items():
        cs = score_by_claim[cid]
        quotes: List[Dict[str, Any]] = []
        for link in graph.links_for_claim(cid):
            q = graph.quotations.get(link.quotation_id)
            if not q:
                continue
            src = graph.sources.get(q.source_id)
            quotes.append(
                {
                    "relation": link.relation,
                    "confidence": round(link.confidence, 2),
                    "text": q.text,
                    "locator": q.locator,
                    "source_title": src.title if src else "(unknown source)",
                    "source_tier": src.tier if src else "",
                    "source_domain": src.domain() if src else "",
                }
            )
