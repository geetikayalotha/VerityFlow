# VerityFlow Architecture

VerityFlow is a Claim Provenance Graph Builder that turns claims, quotations, sources and evidence links into navigable provenance dossiers. The repository uses a Python orchestration layer and a focused native companion so input normalization, deterministic analysis and report rendering remain easy to inspect.

## System flow

`	ext
fixtures or operator input -> parser -> normalized domain records -> analysis engine -> report model -> terminal / JSON / Markdown
` 

## Components

- **Python package** owns command handling, portable parsers, report assembly and example workflows.
- **Native companion** mirrors the central calculation for compact command-line use and implementation parity.
- **Fixtures and docs** define stable, readable examples that make each analysis result reproducible.

## Data contracts

Input records are plain JSON or JSONL documents. The analysis layer uses typed, normalized records; report renderers consume a compact serializable summary. This boundary keeps extensions additive and makes reports suitable for review pipelines.

