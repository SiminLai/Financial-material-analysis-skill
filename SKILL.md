---
name: financial-report-analysis-skill
description: "Evidence-first financial analysis skill for PDF/XLSX: parse documents, extract grounded metrics, compute deterministic risk scores, generate structured reports, run post-report reflection validation, and maintain local RAG/vector artifacts under the workspace cache. This is a local workflow-first repository; Docker and CI are not required unless a production deployment step is added."
version: 1.2.3
author: LLLLLLL
keywords: [financial, parsing, RAG, LangGraph, report, evidence, imputation, reflection, local-workflow]
inputs:
  - file: pdf|xlsx
  - expect: financial statements, earnings releases, investor materials
outputs:
  - report: json (fields: summary, risk_assessment, recommendation, key_points, external_evidence, meta)
  - reflection: json (fields: evaluation_results, internal_feedback, overall_score, external_feedback, conflict_resolution)
requirements:
  - langgraph (optional)
  - PyMuPDF (optional, layout-aware PDF parsing)
  - pdfplumber
  - PyPDF2
  - openpyxl
  - DEEPSEEK_API_KEY (optional for LLM-backed summarization)
cost: low
safe_to_run: true
selector:
  - use_if: "document_type in [annual_report, quarterly_report, earnings_release] or need_evidence_traceability == true"
  - avoid_if: "only_plain_text_extraction_needed or no_financial_metrics_present"
---

# Financial Report Analysis Skill

## What it does

- End-to-end local workflow that parses financial documents (`.pdf`, `.xlsx`), extracts normalized metrics (`company_name`, `revenue`, `net_profit`, `debt_ratio`, `cash_flow`), scores deterministic financial risks, and produces evidence-aware structured JSON reports.
- Stores parsed text, evidence, vector metadata, and per-thread checkpoints under the local workspace cache so the workflow remains auditable and debuggable.
- Supports optional RAG/MCP integration (Tavily/DeepSeek) for external context, but keeps external evidence as supporting-only context that cannot overwrite core metrics or risk scores.
- Runs post-report reflection validation (completeness, consistency, missing-fields, conflict checks) to surface quality issues after report generation.
- Keeps missing critical values as `None` instead of inventing synthetic defaults.

## Current runtime model

This project is intentionally a local Python-based workflow rather than a packaged container service. The repository currently expects direct execution from a Python environment and uses local workspace storage for:

- vector index persistence
- evidence store persistence
- thread-scoped checkpoint files
- transient debug artifacts

Because of this local-first design, Docker and CI are not required unless you later add a production deployment path or release automation.

## Operating model

Run the pipeline in this order:

```text
PDF/XLSX -> parser -> rag_index -> metric extraction -> risk scoring -> report -> reflection validation
```

The graph is assembled in `graph/financial_graph.py` and started from `main.py`.

Runtime input interface:

- Preferred: CLI argument `--input-file <path-to-pdf-or-xlsx>`.
- Alternative: environment variable `INPUT_FILE`.
- Interactive fallback: if neither is provided and the process has a TTY, `main.py` prompts for a file path.
- Optional tracing: pass `--thread-id` or set `THREAD_ID`.

Current implementation flow:

- Resolve input path (`--input-file` -> `INPUT_FILE` -> interactive prompt).
- Parse document into `text/raw_text/cleaned_text/table_regions`.
- Build initial RAG index using text chunks and table chunks (`chunk_type: table`).
- Execute graph: `parser -> rag_index -> metric -> risk -> [optional Tavily MCP external search] -> report -> reflection validation`.
- Persist vector artifacts to `workspace/cache/vector_index.npz` and `workspace/cache/vector_index.npz.meta.json`.
- Write a per-thread SQLite checkpoint file under `workspace/cache/`.

## Inputs and outputs

- Accept `.pdf` and `.xlsx` input files. PDF parsing is layout-aware with PyMuPDF when available and falls back to `pdfplumber`/`PyPDF2`; Excel workbooks use `openpyxl`.
- For PDF input, parser output includes `text`, `raw_text`, `cleaned_text`, `tables`, and `table_regions`.
- `table_regions` schema uses JSON with 2D rows, for example: `{ "page": 10, "bbox": [x0, y0, x1, y1], "rows": [["Metric", "2025"], ["Revenue", "1000"]] }`.
- Extract only values explicitly present in the parsed document. The normalized metric schema is `company_name`, `revenue`, `net_profit`, `debt_ratio`, and `cash_flow`, plus validation metadata.
- Return a report dictionary containing `summary`, `risk_assessment`, `recommendation`, `key_points`, `external_evidence`, and `meta`.
- Treat generated reports as informational analysis, not investment advice. Preserve reported units and periods; do not compare or combine values with different units or reporting periods without making that limitation explicit.

## Run locally

Install dependencies, configure credentials if needed, and run the demo:

```powershell
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY = "your_api_key"  # optional; no key uses deterministic stub LLM responses
python main.py --input-file "examples\your_report.pdf"
```

Environment-variable input example:

```powershell
$env:INPUT_FILE = "examples\your_report.pdf"
python main.py
```

Interactive example (no input arg/env):

```powershell
python main.py
```

`LLMProvider` calls the DeepSeek-compatible chat-completions endpoint. Without `DEEPSEEK_API_KEY`, the project intentionally falls back to stub responses for offline/demo execution.

## Environment variables

- `DEEPSEEK_API_KEY` (optional): enables DeepSeek-compatible LLM summarization/explanations. If unset, the pipeline uses deterministic stub LLM responses.
- `ENABLE_TAVILY` (optional): set to `true` to enable Tavily MCP external search branch.
- `TAVILY_API_KEY` (optional): required when `ENABLE_TAVILY=true`.
- `EMBED_LOCALE` (optional): selects default embedding language for BGE provider, `en` or `zh` (default: `en`).
- `EMBED_MODEL` (optional): explicit embedding model path/name override. When set, it takes precedence over `EMBED_LOCALE`.
- `THREAD_ID` (optional): per-run identifier for checkpoint and trace isolation.

PowerShell examples:

```powershell
$env:EMBED_LOCALE = "zh"
python main.py --input-file "examples\神工股份：锦州神工半导体股份有限公司2025年年度报告.pdf"
```

```powershell
$env:EMBED_LOCALE = "en"
python main.py --input-file "examples\your_report.pdf"
```

## Risk and recommendation rules

Keep the deterministic rules as the source of truth:

- The risk engine penalizes missing metrics, elevated leverage, low or negative cash flow, losses, weak/negative margins, profit-cash-flow mismatches, and implausible revenue values.
- `LOW_CASH_FLOW` uses a ratio-based threshold (`cash_flow / revenue < 0.01`) to reduce unit-sensitivity issues across different reporting scales.
- Risk levels are `LOW` below 0.3, `MEDIUM` from 0.3 to below 0.7, and `HIGH` at or above 0.7.
- LLM output may explain the rule flags but must not change the risk score.
- The final recommendation is enforced by code: `BUY` requires risk below 0.3 plus positive profit and cash flow; `HOLD` requires risk below 0.7; otherwise it is `SELL`.

## Optional external search

Enable Tavily MCP only when external context is needed:

```powershell
$env:ENABLE_TAVILY = "true"
$env:TAVILY_API_KEY = "your_api_key"
python main.py
```

The graph routes to browser search only when the deterministic risk score is at least `0.1`; otherwise it goes directly to report generation. External material is supporting evidence only: never use it to overwrite extracted metrics or the computed risk score, and keep evidence IDs and citations with claims that rely on it.

## Evidence, memory, and extension notes

- Parser and metric nodes save document/table evidence, which the report node converts into readable citations where available.
- The repository includes local memory, vector-store, RAG, imputation, and reflection modules. In the current flow, reflection executes after report generation for post-report validation.
- Missing values remain `None`; they are not silently imputed without evidence and explicit logic.
- Add a new input format by extending `DocumentParserTool` and its provider, then retain the normalized document shape expected by `MetricExtractorTool`.
- Add metrics by updating the extractor schema, validation, deterministic risk rules, report consistency checks, and tests together.

## Vector store and embeddings

- This project supports BGE-based embeddings via `providers/embedding_provider_bge.py`.
- `EMBED_LOCALE` selects `en` or `zh`, and `EMBED_MODEL` overrides the locale default when explicitly set.
- The local `VectorStore` persists data to `workspace/cache/vector_index.npz` and `workspace/cache/vector_index.npz.meta.json`.
- If the dependency is not installed, the project falls back to a deterministic local stub embedder instead of crashing.
- Initial RAG indexing includes both text chunks and table chunks (`chunk_type: table`), allowing page-level retrieval and evidence citation.

## Checkpointing and isolation

During graph construction the skill writes a lightweight LangGraph SQLite checkpoint per `thread_id` for debugging, traceability, and concurrency isolation:

```text
workspace/cache/langgraph_checkpoint_<thread_id>.sqlite
```

This checkpoint is intended for debugging and reproducibility inspection only; it does not serialize node callables, and different threads are isolated by file.

## Repository map

- `main.py`: project entry point and dependency wiring.
- `graph/`: LangGraph nodes, routing, and edges.
- `tools/`: document parsing, extraction, risk, reporting, RAG, and MCP adapters.
- `providers/`: PDF, Excel, LLM, embedding, evidence, and table providers.
- `reflection/` and `memory/`: evidence, retrieval, evaluation, and feedback building blocks.
- `workspace/cache/`: local cached vector index, evidence store, and per-thread checkpoints.
- `examples/`: sample financial PDFs and workbook.

## Not required today: Docker or CI

This repository is currently a local Python workflow used for research and experimentation. It does not require Docker or a CI pipeline for its current operating model.

Docker and CI become relevant only when the project adds one or more of the following:

- hosted deployment
- released package artifacts
- automated test execution in remote environments
- cross-platform release pipelines or production deployment gates

Until then, the lightweight local workflow is the intended operating mode.
