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
