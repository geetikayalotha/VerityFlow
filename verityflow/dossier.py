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
        entries.append(
            DossierEntry(
                claim_id=cid,
                claim_text=claim.text,
                topic=claim.topic,
                verdict=_verdict(cs),
                support_index=cs.support_index,
                diversity=cs.diversity,
                quotations=quotes,
            )
        )

    entries.sort(key=lambda e: (-e.support_index, e.claim_id))

    return Dossier(
        title=title,
        coverage=report.coverage,
        mean_support=round(report.mean_support, 4),
        mean_diversity=round(report.mean_diversity, 4),
        stats=compute_stats(graph).to_dict(),
        entries=entries,
    )


def render_json(dossier: Dossier) -> Dict[str, Any]:
    """Return a JSON-serialisable dict for *dossier*."""
    return {
        "title": dossier.title,
        "summary": {
            "coverage": dossier.coverage,
            "mean_support": dossier.mean_support,
            "mean_diversity": dossier.mean_diversity,
        },
        "graph_stats": dossier.stats,
        "entries": [
            {
                "claim_id": e.claim_id,
                "claim_text": e.claim_text,
                "topic": e.topic,
                "verdict": e.verdict,
                "support_index": e.support_index,
                "diversity": e.diversity,
                "quotations": e.quotations,
            }
            for e in dossier.entries
        ],
    }


_VERDICT_BADGE = {
    "well-supported": "🟢",
    "supported": "🟢",
    "weakly-supported": "🟡",
    "contested": "🟠",
    "unsupported": "⚪",
    "refuted": "🔴",
}


def render_markdown(dossier: Dossier) -> str:
    """Render *dossier* to a self-contained Markdown report."""
    lines: List[str] = []
    lines.append(f"# {dossier.title}")
    lines.append("")
    lines.append(
        f"> Citation coverage **{dossier.coverage:.0%}** · "
        f"mean support **{dossier.mean_support:.2f}** · "
        f"mean diversity **{dossier.mean_diversity:.2f}**"
    )
    lines.append("")

    st = dossier.stats
    lines.append("## Graph at a glance")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Claims | {st['claims']} |")
    lines.append(f"| Sources | {st['sources']} |")
