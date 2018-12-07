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

## Command reference

All commands read from `--input`/`-i` (a file or `-` for stdin) and write to `--output`/`-o` (a file or `-` for stdout).

### `graph`

Compile notes and inspect the graph structure. The `--emit` flag selects what to print:

- `stats` (default) — node/edge counts, relation and tier histograms, dangling/orphan counts, average quotations and sources per claim.
- `adjacency` — a `claim_id → [source_id, ...]` map, handy for feeding external graph viewers.
- `edges` — a flat edge list (`claim ← quotation ← source`) for tabular export.
- `full` — the entire serialised graph (all nodes and links).

### `score`

Compute the full `ScoreReport`: graph-level coverage, mean diversity and mean support, plus a per-claim breakdown with `covered`, `contested`, `diversity`, `support_raw`, `support_index`, source/domain counts and supporting/refuting tallies.

### `dossier`

Assemble the human-facing evidence dossier. `--format markdown` (default) renders a self-contained report with a summary banner, a graph-at-a-glance table and a per-claim section that lists every quotation with its relation, confidence, source and tier. `--format json` emits the same content as a structured document — this is the exact input the .NET summariser expects. `--title` sets the report heading.

### `validate`

Structural pre-flight check. Reports dangling links (edges pointing at a missing claim or quotation) and orphan quotations (spans no link references). Exits `0` when the bundle is clean and `2` when anomalies are found, so it drops straight into a CI gate.

---

## Scoring algorithms in depth

### Citation coverage

Coverage is the fraction of claims that carry **at least one supporting (positive-weight) evidence link**. A claim backed only by `refutes` edges is *not* covered — it is contested. Formally, for a graph with claim set `C`:

```
coverage = |{ c ∈ C : ∃ link l on c with weight(l.relation) > 0 }| / |C|
```

Coverage is the bluntest metric and the first thing a reviewer should look at. A report at 60% coverage has, by definition, 40% of its claims resting on nothing.

### Source diversity

Diversity is the **normalised Shannon entropy** of the provenance *domains* behind a claim. A domain is derived from a source: the URL host if present (stripped of `www.`), else the publisher, else the author. For a claim whose supporting sources fall into domains with counts `n₁ … n_k` (total `N`):

```
H     = -Σ (nᵢ / N) · log₂(nᵢ / N)
diversity = H / log₂(k)          for k > 1, else 0
```

The normalisation by `log₂(k)` maps diversity to `[0, 1]`: a claim cited by a single domain scores `0`; a claim cited equally by `k` distinct domains scores `1`. This is why in the bundled fixture the async-standups claim (three independent domains, one quote each) scores `1.0` while the feature-flags claim (two quotes, one domain) scores `0.0` — same quote count, very different provenance breadth.

### Claim support strength

Support strength condenses every link on a claim into a single bounded index. First it sums the signed, confidence-weighted relation weights:

```
raw = Σ  RELATION_WEIGHT(l.relation) · clamp(l.confidence, 0, 1)
```

Then it squashes `raw` through a logistic function so the index lives in `(0, 1)`:

```
support_index = 1 / (1 + e^(−raw))
```

The squashing gives three intuitive anchors: a claim with **no links** lands at exactly `0.5` (genuinely neutral), a **strongly supported** claim tends toward `1.0`, and a **strongly refuted** claim tends toward `0.0`. Because confidence multiplies the weight, a hedged `supports` at `0.6` confidence contributes less than a firm one at `0.95`.

These three metrics are orthogonal by construction: coverage answers *is it cited at all*, diversity answers *is it cited broadly*, and support answers *how strong is the net evidence*. A claim can be covered but narrow (single-domain), or diverse but weak (lots of low-confidence qualifiers). The dossier verdict combines all three.

---

## The dossier format

The dossier is where numbers become judgements. For each claim VerityFlow assigns a **verdict** from the interplay of coverage, contestation, support and diversity:

| Verdict | Condition |
| --- | --- |
| `well-supported` | covered, `support_index ≥ 0.80`, and `≥ 2` provenance domains |
| `supported` | covered, `support_index ≥ 0.60` |
| `weakly-supported` | covered, but `support_index < 0.60` |
| `contested` | has both supporting and refuting links |
| `unsupported` | no supporting link |
| `refuted` | refuting links and no supporting link |

The Markdown dossier opens with a summary banner (coverage, mean support, mean diversity), a graph-at-a-glance table, and then one section per claim — sorted by descending support so the strongest claims lead — with a verdict badge, the scores, and a table of every quotation, relation, confidence and source. The JSON dossier carries the identical information in a machine-readable tree, and is the contract consumed by the .NET summariser.

---

## The .NET summariser

`VerityFlow.Runtime` is a companion, not a dependency. It reads a JSON dossier and produces an **executive summary**: verdict tallies, the weakest claims that need more citations, and a single **provenance health score** with a letter grade. The health score blends the three graph-level metrics:

```
health = 0.40 · coverage + 0.35 · mean_support + 0.25 · mean_diversity
grade  = A (≥0.85) · B (≥0.70) · C (≥0.55) · D (≥0.40) · F (otherwise)
```

