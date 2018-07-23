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
        return 0.0
    entropy = 0.0
    for count in dist.values():
        p = count / total
        entropy -= p * math.log(p, 2)
    return round(entropy / math.log(len(dist), 2), 4)


def claim_support_strength(graph: ProvenanceGraph, claim_id: str) -> float:
    """Confidence-weighted, bounded support index in [0, 1].

    The raw score is a signed sum of ``relation_weight * confidence`` across
    all links for the claim. It is mapped through a logistic squashing function
    so that a strongly-refuted claim tends to 0 and a strongly-supported claim
    tends to 1, with a neutral (unlinked) claim landing at 0.5.
    """
    raw = sum(l.weight() for l in graph.links_for_claim(claim_id))
    return round(1.0 / (1.0 + math.exp(-raw)), 4)


def _support_raw(graph: ProvenanceGraph, claim_id: str) -> float:
    return round(sum(l.weight() for l in graph.links_for_claim(claim_id)), 4)


def score_claim(graph: ProvenanceGraph, claim_id: str) -> ClaimScore:
    links = graph.links_for_claim(claim_id)
    n_support = sum(1 for l in links if RELATION_WEIGHTS.get(l.relation, 0) > 0)
    n_refute = sum(1 for l in links if RELATION_WEIGHTS.get(l.relation, 0) < 0)
    sources = graph.sources_for_claim(claim_id)
    domains = _domain_distribution(graph, claim_id)

    covered = n_support > 0
    contested = n_refute > 0

    return ClaimScore(
        claim_id=claim_id,
        covered=covered,
