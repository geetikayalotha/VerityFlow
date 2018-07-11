"""Graph compilation: fold research notes into a single provenance graph.

The builder is intentionally forgiving. Duplicate claims, sources and
quotations across notes are de-duplicated by id, so overlapping evidence chains
merge naturally into one graph. Structural anomalies (dangling links, orphan
quotations) are surfaced through :class:`GraphStats` rather than raising.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List

from .model import (
    EvidenceLink,
    ProvenanceGraph,
    Quotation,
    ResearchNote,
    Source,
)


@dataclass
class GraphStats:
    """Structural summary of a compiled provenance graph."""

    claims: int
    sources: int
    quotations: int
    links: int
    relations: Dict[str, int]
    source_tiers: Dict[str, int]
    dangling_links: int
    orphan_quotations: int
    avg_quotations_per_claim: float
    avg_sources_per_claim: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_graph(notes: Iterable[ResearchNote]) -> ProvenanceGraph:
    """Compile *notes* into a :class:`ProvenanceGraph`.

    Nodes are keyed by id; the last definition wins on collision, which keeps
    the operation idempotent when the same note is ingested twice.
    """
    graph = ProvenanceGraph()
    seen_link_ids = set()

    for note in notes:
        graph.claims[note.claim.id] = note.claim
        for s in note.sources:
            graph.sources[s.id] = s
        for q in note.quotations:
            graph.quotations[q.id] = q
        for l in note.links:
