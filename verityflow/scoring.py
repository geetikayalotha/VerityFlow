"""Scoring algorithms for provenance graphs.

Three orthogonal metrics are computed per claim and aggregated to the graph:

* **Citation coverage** — fraction of claims that carry at least one supporting
  (non-refuting) evidence link. A claim with only refuting links counts as
  *contested*, not covered.
* **Source diversity** — normalised Shannon entropy over the provenance domains
  backing a claim. A claim cited by five independent domains scores higher than
  one cited five times by the same domain.
* **Claim support strength** — the signed, confidence-weighted sum of relation
  weights, squashed into a bounded 0..1 support index.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

from .model import ProvenanceGraph, RELATION_WEIGHTS


@dataclass
class ClaimScore:
    claim_id: str
    covered: bool
    contested: bool
    diversity: float
    support_raw: float
    support_index: float
    n_sources: int
    n_domains: int
    n_supporting: int
    n_refuting: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreReport:
    coverage: float
    mean_diversity: float
    mean_support: float
    claims: List[ClaimScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage": round(self.coverage, 4),
            "mean_diversity": round(self.mean_diversity, 4),
            "mean_support": round(self.mean_support, 4),
            "claims": [c.to_dict() for c in self.claims],
        }


def _domain_distribution(graph: ProvenanceGraph, claim_id: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for src in graph.sources_for_claim(claim_id):
        d = src.domain()
        counts[d] = counts.get(d, 0) + 1
    return counts


def source_diversity(graph: ProvenanceGraph, claim_id: str) -> float:
    """Normalised Shannon entropy of provenance domains for *claim_id*.

    Returns 0.0 for a claim backed by a single domain (or none) and approaches
    1.0 as evidence spreads across many equally-weighted domains.
    """
    dist = _domain_distribution(graph, claim_id)
    total = sum(dist.values())
    if total == 0 or len(dist) <= 1:
