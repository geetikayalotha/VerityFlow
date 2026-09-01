# VerityFlow Design Notes

## Product intent
VerityFlow makes turns claims, quotations, sources and evidence links into navigable provenance dossiers practical in a reviewable developer workflow. It favors compact source data, deterministic scoring and reports that retain the evidence behind every result.

## Design principles
1. **Traceable results** — every score connects to normalized input records and named calculations.
2. **Portable artifacts** — JSON and Markdown reports travel cleanly through pull requests and release notes.
3. **Compositional analysis** — parsers, domain models, metrics and renderers can evolve independently.
4. **Useful defaults** — bundled fixtures demonstrate realistic workflows without configuration overhead.

## Extension seams
New record adapters belong at the ingestion boundary, new metrics attach to the analysis summary, and new renderers consume the existing report model. This keeps integrations focused and avoids cross-cutting rewrites.

