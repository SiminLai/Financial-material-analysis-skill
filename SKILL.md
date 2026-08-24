name: financial-report-analysis-skill
description: "Parse financial PDF/XLSX, extract normalized metrics, run deterministic risk scoring, and produce evidence-cited JSON reports. Optional RAG/MCP integration provides external context without overriding parsed facts. Designed for auditable, evidence-first analyses of financial filings."
version: 1.0.5
author: LLLLLLL
keywords: [financial, parsing, RAG, LangGraph, report, evidence, imputation, reflection]
inputs:
	- file: pdf|xlsx
	- expect: financial statements, earnings releases, investor materials
outputs:
	- report: json (fields: summary, risk_assessment, recommendation, key_points, external_evidence, meta)
requirements:
	- langgraph (optional)
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

- End-to-end LangGraph workflow that parses local financial documents (`.pdf`, `.xlsx`), extracts normalized metrics (`company_name`, `revenue`, `net_profit`, `debt_ratio`, `cash_flow`), scores deterministic financial risks, and produces evidence-aware structured JSON reports.
- Persists all important artifacts as `Evidence` (with `evidence_id`) so external RAG results and internal parsing/imputation steps are traceable and citable inside final reports.
- Supports optional RAG/MCP integration (Tavily/DeepSeek) for external context; compresses and summarizes retrieved items and injects them into the pipeline without overwriting core deterministic metrics.
- Provides reflection/evaluation hooks (completeness, consistency, missing-fields) and an imputer for computed metrics (e.g., debt ratio) to improve robustness.

## When to use

- Automating structured extraction and analysis of annual/quarterly reports, earnings releases, and investor materials where reproducible traceability of evidence is required.
- Augmenting deterministic rule-based risk scoring with contextual external evidence (RAG) while keeping decisions auditable and grounded in parsed values.
- Rapid prototyping of LangGraph + RAG + LLM pipelines where you need clear separation between parsed facts, inferred values, external evidence, and LLM explanations.

## Important capabilities

- Document parsing: PDF and Excel table/text extraction using `pdfplumber`/`PyPDF2` and `openpyxl` providers.
- Structured metric extraction and strict validation (Pydantic-backed schemas and rule checks).
- Deterministic risk engine with explicit rules and enforced recommendation logic (`BUY`/`HOLD`/`SELL`).
- Evidence-first design: `EvidenceStore` + `EvidenceBuilder` persist parsed text, table cells, RAG items, imputer outputs, and risk flags with `evidence_id` for citation in reports.
- RAG and MCP adapters: optional external search via Tavily MCP and DeepSeek-compatible LLM integration; retrieval is summarized and linked into reports but cannot override core metrics.
- Reflection & evaluation: modular evaluators (missing/completeness/consistency) and conflict-resolution hooks to surface issues before final reporting.
- Imputation: best-effort metric imputation (e.g., debt ratio) from existing parsed evidence, with imputation evidence persisted.
- Reproducible graph construction: LangGraph-based node graph with native checkpointer integration when available; fallback components for environments without LangGraph.
- Production readiness features: LLM stub/production modes, retry/backoff for remote LLMs, safe release cleanup script, and guidance for GitHub publishing.

## Operating model

Run the pipeline in this order:

```text
PDF/XLSX -> parser -> metric extraction -> risk scoring -> [Tavily MCP, if enabled] -> report
```

The graph is assembled in `graph/financial_graph.py` and started from `main.py`. `main.py` currently uses the bundled Q4 earnings-release PDF as its demo input. Change `init_state["input_file"]` or invoke the compiled graph with another local `.pdf` or `.xlsx` file to analyze a different document.

## Inputs and outputs

- Accept `.pdf` and `.xlsx` input files. PDF text and tables are parsed with `pdfplumber`/`PyPDF2`; Excel workbooks use `openpyxl`.
- Extract only values explicitly present in the parsed document. The normalized metric schema is `company_name`, `revenue`, `net_profit`, `debt_ratio`, and `cash_flow`, plus validation metadata.
- Return a report dictionary containing `summary`, `risk_assessment`, `recommendation`, `key_points`, `external_evidence`, and `meta`.
- Treat generated reports as informational analysis, not investment advice. Preserve reported units and periods; do not compare or combine values with different units or reporting periods without making that limitation explicit.

## Run locally

Install the pinned dependencies, configure credentials as needed, then run the demo:

```powershell
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY = "your_api_key"  # optional; no key uses deterministic stub LLM responses
python main.py
```

`LLMProvider` calls the DeepSeek-compatible chat-completions endpoint. Without `DEEPSEEK_API_KEY`, the project intentionally falls back to stub responses for offline/demo execution; the output is not a meaningful financial analysis.

## Risk and recommendation rules

Keep the deterministic rules as the source of truth:

- The risk engine penalizes missing metrics, elevated leverage, low or negative cash flow, losses, weak/negative margins, profit-cash-flow mismatches, and implausible revenue values.
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

With both variables set, `main.py` registers the `tavily` MCP server defined in `config/mcp.json`. The graph routes to browser search when the deterministic risk score is at least `0.1`; otherwise it goes directly to reporting. External material is supporting evidence only: never use it to overwrite extracted metrics or the computed risk score, and keep evidence IDs/citations with claims that rely on it.

## Evidence, memory, and extension notes

- Parser and metric nodes save document/table evidence, which the report node converts into readable citations where available.
- The repository includes local memory, vector-store, RAG, imputation, and reflection modules. Some are initialized for experimentation, but the current graph edges do **not** execute `impute` or `reflect`; connect them deliberately in `graph/edges.py` before representing their results as part of the normal pipeline.
- Add a new input format by extending `DocumentParserTool` and its provider, then retain the normalized document shape expected by `MetricExtractorTool`.
- Add metrics by updating the extractor schema, validation, deterministic risk rules, report consistency checks, and tests together. Do not rely on an LLM-only value for a decision-critical calculation.

## Repository map

- `main.py`: demo entry point and dependency wiring.
- `graph/`: LangGraph nodes, routing, and edges.
- `tools/`: document parsing, extraction, risk, reporting, RAG, and MCP adapters.
- `providers/`: PDF, Excel, LLM, embedding, table, and evidence providers.
- `reflection/` and `memory/`: evidence, retrieval, evaluation, and feedback building blocks.
- `examples/`: sample financial PDFs and workbook.
