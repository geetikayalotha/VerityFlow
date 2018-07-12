# VerityFlow — Claim Provenance Graph Builder

VerityFlow turns a pile of research notes into a rigorous, inspectable **provenance graph**. Every assertion you make becomes a *claim* node; every document you lean on becomes a *source*; every verbatim span you pull becomes a *quotation*; and every judgement you form — "this backs the claim", "this contradicts it", "this only qualifies it" — becomes a typed *evidence link*. From that graph VerityFlow computes **citation coverage**, **source diversity** and **claim support strength**, then assembles a publication-ready **evidence dossier** in Markdown or JSON. A companion .NET runtime reads the dossier and stamps it with an executive **provenance health grade**.

If you have ever finished a report and wondered *which of my claims are actually cited, and how well*, VerityFlow answers that question mechanically and reproducibly.

![Provenance graph](docs/assets/provenance-graph.svg)

VerityFlow is deliberately small and dependency-free. The core is a Python 3.11 package (`verityflow`) built entirely on the standard library; the summariser is a single-file .NET 9 console app that uses only the base class library. There is no database, no service to run, no network call anywhere in the pipeline. You point it at a JSON bundle of notes and you get back structured verdicts.

---

## Table of contents

- [Why provenance graphs](#why-provenance-graphs)
- [The mental model](#the-mental-model)
- [Architecture](#architecture)
- [Install and run](#install-and-run)
- [The data schema](#the-data-schema)
- [Command reference](#command-reference)
- [Scoring algorithms in depth](#scoring-algorithms-in-depth)
- [The dossier format](#the-dossier-format)
- [The .NET summariser](#the-net-summariser)
- [CLI recipes](#cli-recipes)
- [Operations and exit codes](#operations-and-exit-codes)
- [Extension seams](#extension-seams)
- [Design principles](#design-principles)
- [Glossary](#glossary)

---

## Why provenance graphs

Most citation tooling treats references as a flat bibliography: a list at the end of a document with no machine-readable relationship to the sentences that depend on them. That flatness hides three failure modes that VerityFlow is built to expose:

1. **Uncited claims.** A confident sentence with no attached evidence reads exactly like a well-supported one. A flat reference list cannot tell them apart. A provenance graph can: an uncited claim is simply a node with no inbound supporting edge.

2. **Monoculture citations.** Five citations that all trace back to the same author, publisher or domain give the *appearance* of thorough sourcing while providing almost none of its substance. VerityFlow measures the **diversity** of the provenance domains behind each claim, so a single-source claim cannot masquerade as broadly supported.

3. **Buried contradictions.** When a source you cite actually *undercuts* your claim, that tension should be surfaced, not smoothed over. VerityFlow models `refutes` and `qualifies` relations as first-class edges and folds them into a signed support index, so a contested claim is flagged rather than quietly averaged away.

By representing the whole apparatus as a directed graph, VerityFlow makes these properties *computable*. Coverage becomes a ratio. Diversity becomes an entropy. Support becomes a bounded index. And the dossier turns those numbers back into prose a human reviewer can act on.

---

## The mental model

VerityFlow has exactly four node kinds and one edge kind. Keeping the vocabulary this small is intentional — it is what lets the whole tool stay dependency-free and auditable.

```
   Source ──contains──▶ Quotation ──[relation]──▶ Claim
   (paper,              (verbatim span,           (assertion under
    dataset,             page/timestamp            scrutiny)
    interview)           locator)
```

- A **Source** is anything citable: a paper, a dataset, an interview transcript, a webpage, a book. It carries a *tier* (`primary`, `secondary`, `tertiary`) and enough metadata to derive a **provenance domain** used for diversity scoring.
- A **Quotation** is a verbatim span lifted from exactly one source, optionally with a *locator* (page number, paragraph marker, media timestamp).
- A **Claim** is the assertion you are trying to justify. It has a *topic* and a *stance* (`asserted`, `disputed`, `hypothesis`).
- An **EvidenceLink** is a typed, confidence-weighted edge from a quotation to a claim. Its *relation* is one of `supports`, `qualifies`, `context` or `refutes`.

The ingestion unit is the **ResearchNote**: one claim bundled with the sources, quotations and links that back or challenge it. You author notes; VerityFlow folds a list of notes into a single de-duplicated **ProvenanceGraph**. Because nodes are keyed by deterministic ids, ingesting the same note twice is idempotent, and two notes that cite the same source merge that source into one shared node automatically.

---

## Architecture

VerityFlow is a straight pipeline with four stages. Each stage is a pure function over the previous stage's output, which makes the whole thing trivially testable by hand and trivially reproducible.

![Pipeline](docs/assets/pipeline.svg)

```
                    ┌──────────────────────────── Python core (verityflow) ────────────────────────────┐
                    │                                                                                   │
  research-notes    │   model.py            graph.py           scoring.py          dossier.py           │
  .json  ─────────▶ │   parse & id ───▶ build_graph ───▶ score_graph ───▶ build_dossier ───▶ render_*   │
                    │   (ResearchNote)   (ProvenanceGraph)  (ScoreReport)   (Dossier)      md / json     │
                    │                                                                          │         │
                    └──────────────────────────────────────────────────────────────────────── │ ───────┘
                                                                                               │
                                                                                     dossier.json
                                                                                               │
                    ┌──────────────── .NET runtime (VerityFlow.Runtime) ──────────────────────▼───────┐
                    │   DossierReader.cs ──▶ Summariser.cs ──▶ Program.cs                                │
                    │   parse JSON          health score + grade   text / json summary + exit code      │
                    └───────────────────────────────────────────────────────────────────────────────┘
```

Module responsibilities:

| Module | Responsibility |
| --- | --- |
| `verityflow/model.py` | Dataclasses for every node/edge, deterministic id synthesis, note parsing. |
| `verityflow/graph.py` | Fold notes into a `ProvenanceGraph`; compute structural `GraphStats`; export adjacency/edge lists. |
| `verityflow/scoring.py` | Citation coverage, source diversity (Shannon entropy), support strength (logistic squash). |
| `verityflow/dossier.py` | Assemble per-claim verdicts and render Markdown/JSON dossiers. |
| `verityflow/cli.py` | Argument parsing, stdin/stdout plumbing, four subcommands. |
| `runtime/DossierReader.cs` | Parse the JSON dossier with `System.Text.Json`. |
| `runtime/Summariser.cs` | Blend coverage/support/diversity into a health score and letter grade. |
| `runtime/Program.cs` | CLI entry point; text or JSON output; grade-driven exit code. |

The two runtimes are decoupled by a **JSON contract** — the dossier. Python never imports anything from .NET and vice versa. You can run the Python half alone, feed the dossier to your own tooling, or run the .NET summariser against any JSON that matches the dossier shape.

---

## Install and run

There is nothing to install. Clone the repository and run the modules in place.

Python core (requires Python 3.11+):

```bash
# structural stats for the bundled fixture
python -m verityflow graph -i examples/research-notes.json

# full score report
python -m verityflow score -i examples/research-notes.json

# a Markdown dossier
python -m verityflow dossier -i examples/research-notes.json --title "Q3 Claims Audit"
```

.NET summariser (requires the .NET 9 SDK):

```bash
# build once
dotnet build runtime/VerityFlow.Runtime.csproj -c Release --nologo

# pipe a JSON dossier straight through the summariser
python -m verityflow dossier -i examples/research-notes.json --format json \
  | dotnet run --project runtime/VerityFlow.Runtime.csproj -c Release --no-build
```

The `Makefile` wraps all of this: `make graph`, `make score`, `make dossier`, `make summary`, `make build`, `make validate`.

---

## The data schema

Input is a single JSON array of research notes (or an object with a `notes` array). Each note has the following shape. Every id is optional — omit it and VerityFlow synthesises a stable id by hashing the content, so the same input always produces the same graph.

```jsonc
{
  "claim": {
    "text": "Feature flags reduce rollback frequency.",   // required
    "topic": "release-engineering",                        // default: "general"
    "author": "",                                          // optional
    "stance": "asserted"                                   // asserted | disputed | hypothesis
  },
  "sources": [
    {
      "title": "Progressive Delivery Benchmarks",          // required
      "kind": "dataset",                                   // document | dataset | interview | webpage | book
      "author": "DeployMetrics",
      "year": 2023,
      "publisher": "DeployMetrics",
      "url": "https://deploymetrics.example/benchmarks",
      "tier": "primary"                                    // primary | secondary | tertiary
    }
  ],
  "quotations": [
    {
      "source_title": "Progressive Delivery Benchmarks",   // links quote to a source by title...
      "text": "Pipelines with flags rolled back 42% less often.",
      "locator": "fig 2"                                   // page / timestamp / paragraph
    }
  ],
  "links": [
    {
      "quotation_text": "Pipelines with flags rolled back 42% less often.",
      "relation": "supports",                              // supports | qualifies | context | refutes
      "confidence": 0.85                                   // 0..1
    }
  ]
}
```

**Reference resolution.** Quotations may reference their source by `source_id` or, more ergonomically, by `source_title`. Links may reference their quotation by `quotation_id` or by `quotation_text`. VerityFlow resolves the friendly forms into ids during parsing. If a reference cannot be resolved, the resulting edge is *dangling* and is reported by `validate` rather than crashing the pipeline.

**Relation vocabulary and weights.** Each relation carries a signed weight that feeds support strength:

| Relation | Weight | Meaning |
| --- | --- | --- |
| `supports` | `+1.0` | The quotation directly backs the claim. |
| `qualifies` | `+0.5` | The quotation supports the claim under conditions. |
| `context` | `+0.25` | The quotation provides background, not direct proof. |
| `refutes` | `-1.0` | The quotation contradicts the claim. |

An invalid relation is a hard error at parse time — the vocabulary is closed on purpose.

---

