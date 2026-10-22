"""Core data model for VerityFlow provenance graphs.

The model expresses four node kinds and the edges that bind them:

* :class:`Claim`      — an assertion made in a document.
* :class:`Source`     — a document, dataset or artefact that can be cited.
* :class:`Quotation`  — a verbatim span extracted from a source.
* :class:`EvidenceLink` — a typed edge stating how a quotation relates to a
  claim (supports, refutes, qualifies or context).

A :class:`ResearchNote` is the ingestion unit: it carries one claim plus the
quotations and sources that back (or challenge) it. A collection of research
notes is compiled into a :class:`ProvenanceGraph`.

All structures are plain dataclasses so they serialise cleanly to JSON with the
standard library only.
"""

from __future__ import annotations

import math

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional


# Relation vocabulary used by evidence links. The weight expresses how much a
# given relation contributes to (or detracts from) claim support strength.
RELATION_WEIGHTS: Dict[str, float] = {
    "supports": 1.0,
    "qualifies": 0.5,
    "context": 0.25,
    "refutes": -1.0,
}

VALID_RELATIONS = tuple(RELATION_WEIGHTS.keys())

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Return a stable, lowercase slug for *text*."""
    s = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return s or "item"


def stable_id(prefix: str, *parts: str) -> str:
    """Deterministic short id derived from *parts* (order-sensitive)."""
    digest = hashlib.sha1("\u241f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:10]}"


@dataclass
class Source:
    """A citable artefact: paper, article, dataset, interview, etc."""

    id: str
    title: str
    kind: str = "document"  # document | dataset | interview | webpage | book
    author: str = ""
    year: Optional[int] = None
    publisher: str = ""
    url: str = ""
    tier: str = "secondary"  # primary | secondary | tertiary

    def domain(self) -> str:
        """Coarse provenance domain used for diversity scoring."""
        if self.url:
            m = re.match(r"https?://([^/]+)/?", self.url)
            if m:
                host = m.group(1).lower()
                return host[4:] if host.startswith("www.") else host
        if self.publisher:
            return slugify(self.publisher)
        return slugify(self.author or "unknown")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Quotation:
    """A verbatim span extracted from a :class:`Source`."""

    id: str
    source_id: str
    text: str
    locator: str = ""  # page, timestamp, paragraph marker, etc.

    def word_count(self) -> int:
        return len([w for w in self.text.split() if w])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    """An assertion under scrutiny."""

    id: str
    text: str
    topic: str = "general"
    author: str = ""
    stance: str = "asserted"  # asserted | disputed | hypothesis

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceLink:
    """Typed edge from a :class:`Quotation` to a :class:`Claim`."""

    id: str
    claim_id: str
    quotation_id: str
    relation: str = "supports"
    confidence: float = 1.0  # 0..1 annotator confidence

    def weight(self) -> float:
        base = RELATION_WEIGHTS.get(self.relation, 0.0)
        return base * max(0.0, min(1.0, self.confidence))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchNote:
    """Ingestion unit binding one claim to its supporting material."""

    claim: Claim
    sources: List[Source] = field(default_factory=list)
    quotations: List[Quotation] = field(default_factory=list)
    links: List[EvidenceLink] = field(default_factory=list)

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "ResearchNote":
        """Build a note from a loosely-typed dict (as loaded from JSON).

        Missing ids are synthesised deterministically so the same input always
        yields the same graph.
        """
        c = raw["claim"]
        claim_text = c["text"]
        claim = Claim(
            id=c.get("id") or stable_id("claim", claim_text),
            text=claim_text,
            topic=c.get("topic", "general"),
            author=c.get("author", ""),
            stance=c.get("stance", "asserted"),
        )

        sources: List[Source] = []
        for s in raw.get("sources", []):
            title = s["title"]
            sources.append(
                Source(
                    id=s.get("id") or stable_id("src", title, str(s.get("year", ""))),
                    title=title,
                    kind=s.get("kind", "document"),
                    author=s.get("author", ""),
                    year=s.get("year"),
                    publisher=s.get("publisher", ""),
                    url=s.get("url", ""),
                    tier=s.get("tier", "secondary"),
                )
            )
        src_by_key = {s.title: s.id for s in sources}

        quotations: List[Quotation] = []
        for q in raw.get("quotations", []):
            sid = q.get("source_id")
            if not sid and q.get("source_title"):
                sid = src_by_key.get(q["source_title"], "")
            qtext = q["text"]
            quotations.append(
                Quotation(
                    id=q.get("id") or stable_id("quo", qtext),
                    source_id=sid or "",
                    text=qtext,
                    locator=q.get("locator", ""),
                )
            )
        quo_by_text = {q.text: q.id for q in quotations}

        links: List[EvidenceLink] = []
        for l in raw.get("links", []):
            qid = l.get("quotation_id")
            if not qid and l.get("quotation_text"):
                qid = quo_by_text.get(l["quotation_text"], "")
            relation = l.get("relation", "supports")
            if relation not in VALID_RELATIONS:
                raise ValueError(
                    f"invalid relation {relation!r}; expected one of {VALID_RELATIONS}"
                )
            links.append(
                EvidenceLink(
                    id=l.get("id")
                    or stable_id("lnk", claim.id, qid or "", relation),
                    claim_id=claim.id,
                    quotation_id=qid or "",
                    relation=relation,
                    confidence=_confidence(l.get("confidence", 1.0), l.get("id") or ""),
                )
            )

        return ResearchNote(
            claim=claim,
            sources=sources,
            quotations=quotations,
            links=links,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "quotations": [q.to_dict() for q in self.quotations],
            "links": [l.to_dict() for l in self.links],
        }


@dataclass
class ProvenanceGraph:
    """A compiled directed graph over claims, quotations and sources."""

    claims: Dict[str, Claim] = field(default_factory=dict)
    sources: Dict[str, Source] = field(default_factory=dict)
    quotations: Dict[str, Quotation] = field(default_factory=dict)
    links: List[EvidenceLink] = field(default_factory=list)

    # ------------------------------------------------------------------ views
    def links_for_claim(self, claim_id: str) -> List[EvidenceLink]:
        return [l for l in self.links if l.claim_id == claim_id]

    def quotations_for_claim(self, claim_id: str) -> List[Quotation]:
        out: List[Quotation] = []
        seen = set()
        for l in self.links_for_claim(claim_id):
            q = self.quotations.get(l.quotation_id)
            if q and q.id not in seen:
                seen.add(q.id)
                out.append(q)
        return out

    def sources_for_claim(self, claim_id: str) -> List[Source]:
        out: List[Source] = []
        seen = set()
        for q in self.quotations_for_claim(claim_id):
            s = self.sources.get(q.source_id)
            if s and s.id not in seen:
                seen.add(s.id)
                out.append(s)
        return out

    def dangling_links(self) -> List[EvidenceLink]:
        """Links whose quotation or claim is missing from the graph."""
        bad = []
        for l in self.links:
            if l.claim_id not in self.claims or l.quotation_id not in self.quotations:
                bad.append(l)
        return bad

    def orphan_quotations(self) -> List[Quotation]:
        """Quotations that no link references."""
        used = {l.quotation_id for l in self.links}
        return [q for q in self.quotations.values() if q.id not in used]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": {k: v.to_dict() for k, v in self.claims.items()},
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "quotations": {k: v.to_dict() for k, v in self.quotations.items()},
            "links": [l.to_dict() for l in self.links],
        }


def load_notes(payload: Iterable[Dict[str, Any]]) -> List[ResearchNote]:
    """Parse an iterable of raw note dicts into :class:`ResearchNote` objects."""
    return [ResearchNote.from_dict(item) for item in payload]


def _confidence(value, link_id: str) -> float:
    """A weight must be a finite number in [0, 1]; null keeps the documented default."""
    if value is None:
        return 1.0
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"link {link_id!r} has a non-numeric confidence: {value!r}") from exc
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(
            f"link {link_id!r} confidence must be finite and in [0, 1], got {value!r}"
        )
    return number
