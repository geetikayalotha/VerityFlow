"""VerityFlow — Claim Provenance Graph Builder.

VerityFlow turns a bundle of research notes into a directed provenance graph
linking claims, sources, quotations and evidence links, then scores citation
coverage, source diversity and claim support strength to emit Markdown/JSON
evidence dossiers.

The package is dependency-free and relies only on the Python standard library.
"""

from .model import (
    Claim,
    Source,
    Quotation,
    EvidenceLink,
