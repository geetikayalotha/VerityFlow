# VerityFlow Architecture

VerityFlow is a Claim Provenance Graph Builder that turns claims, quotations, sources and evidence links into navigable provenance dossiers. The repository uses a Python orchestration layer and a focused native companion so input normalization, deterministic analysis and report rendering remain easy to inspect.

## System flow

`	ext
fixtures or operator input -> parser -> normalized domain records -> analysis engine -> report model -> terminal / JSON / Markdown
` 

