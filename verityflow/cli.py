"""VerityFlow command-line interface.

Subcommands
-----------
* ``graph``   — compile research notes and print structural stats (or export
  the adjacency / edge-list skeleton).
* ``score``   — compute citation coverage, source diversity and support
  strength; emit a JSON score report.
* ``dossier`` — assemble an evidence dossier and render it as Markdown or JSON.
* ``validate``— check note bundles for structural anomalies before ingestion.

All commands read newline-delimited-free JSON (a single array of notes) from a
file or stdin, and write to a file or stdout. The tool is dependency-free.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List

from .graph import build_graph, compute_stats, to_adjacency, to_edge_list
from .model import load_notes
from .scoring import score_graph
from .dossier import build_dossier, render_json, render_markdown


def _read_input(path: str) -> Any:
    if path == "-" or not path:
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_output(path: str, text: str) -> None:
    if path == "-" or not path:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _load_graph(path: str):
    payload = _read_input(path)
    if isinstance(payload, dict) and "notes" in payload:
        payload = payload["notes"]
    if not isinstance(payload, list):
        raise ValueError("input must be a JSON array of research notes")
    notes = load_notes(payload)
    return build_graph(notes)


def cmd_graph(args: argparse.Namespace) -> int:
    graph = _load_graph(args.input)
    if args.emit == "stats":
        payload = compute_stats(graph).to_dict()
    elif args.emit == "adjacency":
        payload = to_adjacency(graph)
    elif args.emit == "edges":
        payload = to_edge_list(graph)
    else:  # full
        payload = graph.to_dict()
    _write_output(args.output, json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    graph = _load_graph(args.input)
    report = score_graph(graph)
    _write_output(
        args.output, json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    )
    return 0


def cmd_dossier(args: argparse.Namespace) -> int:
    graph = _load_graph(args.input)
    dossier = build_dossier(graph, title=args.title)
    if args.format == "json":
        text = json.dumps(render_json(dossier), indent=2, ensure_ascii=False)
    else:
        text = render_markdown(dossier)
    _write_output(args.output, text)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    graph = _load_graph(args.input)
    dangling = graph.dangling_links()
    orphans = graph.orphan_quotations()
    report = {
        "ok": not dangling and not orphans,
        "claims": len(graph.claims),
        "dangling_links": [l.id for l in dangling],
        "orphan_quotations": [q.id for q in orphans],
    }
    _write_output(args.output, json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verityflow",
        description="Claim Provenance Graph Builder — compile research notes "
        "into an evidence graph and emit dossiers.",
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
