---
name: financial-report-analysis-skill
description: Analyze PDF or XLSX financial documents, including annual and quarterly reports, earnings releases, financial statements, and investor materials. Extract strictly grounded company, revenue, net-profit, debt-ratio, and operating-cash-flow metrics; score deterministic financial risks; and generate evidence-aware JSON reports. Use when working with this repository to run, extend, debug, or evaluate its LangGraph-based financial-document analysis pipeline, including its optional DeepSeek and Tavily MCP integrations.
---

# Financial Report Analysis Skill

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
