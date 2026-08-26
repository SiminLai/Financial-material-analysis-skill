# Financial Report Analysis Skill

A local, evidence-first financial analysis workflow for PDF/XLSX inputs. It parses documents, extracts grounded metrics, computes deterministic risk scores, generates structured reports, runs reflection validation after report generation, and persists local RAG artifacts to the workspace cache.

This repository is a research/local-automation skill rather than a packaged SaaS service. It does not currently require Docker or a CI pipeline for normal local use.

---

## What it does

- Parses PDF and Excel financial reports
- Preserves `raw_text`, `cleaned_text`, and `table_regions` for traceability
- Extracts normalized metrics such as `company_name`, `revenue`, `net_profit`, `debt_ratio`, and `cash_flow`
- Prioritizes table-based extraction from `table_regions` when structured evidence is present
- Runs deterministic risk scoring with explicit validation and review gates
- Builds a local vector index from chunked text and table payloads
- Persists vector metadata under `workspace/cache/`
- Stores per-thread LangGraph checkpoints under `workspace/cache/`
- Uses reflection to evaluate completeness, consistency, and missing-field issues after report generation
- Treats external evidence as supporting-only and never lets it overwrite core metrics or risk values

---

## Current architecture

```text
PDF/XLSX -> parser -> rag_index -> metric extraction -> risk scoring -> report -> reflection validation
```

Key implementation notes:

- The graph is a deterministic state workflow, not a pure ReAct loop and not a strict plan-and-execute agent.
- `rag_index` is part of the normal execution path and writes document chunks to the vector store.
- The vector store persists as `workspace/cache/vector_index.npz` and `workspace/cache/vector_index.npz.meta.json`.
- Checkpoints are created per `thread_id` to avoid cross-task contamination.
- Missing critical values such as `debt_ratio` remain `None` and trigger review instead of defaulting to synthetic numbers.

---

## Supported inputs

- Annual reports
- Quarterly reports
- Earnings releases
- Financial statements
- Investor presentations
- Excel tables with financial values

Supported file types:

- `.pdf`
- `.xlsx`

---

## Local setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the skill from the repo root:

```bash
python main.py --input-file "examples/your_report.pdf"
```

PowerShell:

```powershell
python main.py --input-file "examples\your_report.pdf"
```

Optional environment variables:

```powershell
$env:EMBED_LOCALE = "zh"
$env:INPUT_FILE = "examples\your_report.pdf"
python main.py
```

---

## Optional external search

External search is disabled by default.

Enable Tavily only when needed:

```powershell
$env:ENABLE_TAVILY = "true"
$env:TAVILY_API_KEY = "your_api_key"
python main.py --input-file "examples\your_report.pdf"
```

The external layer is supporting evidence only; it does not override extracted metrics or the deterministic risk score.

---

## Embeddings and vector cache

- BGE embeddings are supported via `providers/embedding_provider_bge.py`.
- `EMBED_LOCALE` selects `en` or `zh` when a locale-specific model is needed.
- `EMBED_MODEL` can override the locale-specific default.
- If the runtime does not have `FlagEmbedding`, the project falls back to a deterministic local stub embedder.
- The vector store is persisted under `workspace/cache/` and is designed for local retrieval and debugging.

---

## Checkpointing

Each graph run can create a SQLite checkpoint keyed by `thread_id`, for example:

```text
workspace/cache/langgraph_checkpoint_<thread_id>.sqlite
```

This is a local debugging and isolation mechanism. Different threads write separate checkpoint files and are not intended to be shared across tasks.

---

## Operational status

This repo is currently meant to run as a local Python workflow, not as a containerized microservice. As a result:

- No Dockerfile is required for the current local-research workflow.
- No CI pipeline is required unless you later add automated release packaging, remote deployment, or a hosted service layer.

This keeps the project lightweight and easier to debug while the skill is still evolving.

---

## Notes and boundaries

- Missing critical fields remain `None` instead of being silently defaulted.
- `needs_review` is raised when critical metrics are absent or inconsistent.
- Final recommendation is enforced by logic, not left unconstrained to model output.
- Generated analyses are informational only and not investment or audit advice.

---

## Runtime artifact locations

```text
workspace/
  cache/
    evidence_store.json
    vector_index.npz
    vector_index.npz.meta.json
    langgraph_checkpoint_<thread_id>.sqlite
```

These files are local artifacts for debugging and retrieval; they can be cleaned manually if desired.

