# Financial Report Analysis Skill

An evidence-first financial analysis skill built with LangGraph for PDF/XLSX documents. It extracts grounded metrics, computes deterministic risk scores, generates structured reports, and then runs reflection-based post-report validation. RAG/MCP context is optional and treated as supporting evidence only.

---

## Features

- Parse financial documents from PDF and Excel (`.xlsx`) files
- Layout-aware PDF parsing with `raw_text` (audit), `cleaned_text` (for chunking/RAG), and `table_regions` (2D JSON table rows)
- Extract key financial metrics such as revenue, net profit, debt ratio, and cash flow
- Prioritize structured extraction from `table_regions` when table evidence is available
- Perform explainable financial risk analysis
- Generate structured financial analysis reports
- Run post-report reflection validation (completeness, consistency, missing fields, conflict checks)
- Unified document parser for multi-format input
- LangGraph-based workflow orchestration
- Optional MCP external search support (disabled by default)

---

## Supported Inputs

Supported document types include:

- Annual Reports
- Quarterly Reports
- Earnings Releases
- Financial Statements
- Investor Presentations
- Excel-based Financial Tables

Supported file formats:

- `.pdf`
- `.xlsx`

---

## Project Structure

```
financial-report-analysis-skill/

├── config/
├── examples/
├── graph/
├── mcp_local/
├── providers/
├── skills/
├── state/
├── tools/
├── validators/
├── workflow/
├── main.py
└── requirements.txt
```

---

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

### DeepSeek API

Configure your DeepSeek API key through an environment variable.

Linux/macOS:

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
```

---

### Optional MCP External Search

External search is disabled by default.

To enable MCP-based Tavily search, configure:

Linux/macOS:

```bash
export ENABLE_TAVILY=true
export TAVILY_API_KEY="your_api_key"
```

Windows PowerShell:

```powershell
$env:ENABLE_TAVILY="true"
$env:TAVILY_API_KEY="your_api_key"
```

When enabled, the Skill may send the following information to the configured search service:

- Company name
- Risk score
- Financial risk factors
- Financial search keywords

The Skill does **not** upload:

- Original PDF documents
- Original Excel files
- Complete document contents

---

## Usage

Run the Skill from the project root:

```bash
python main.py
```

By default:

- External search is disabled.
- Financial reports are generated using local document analysis only.
- Reflection validation summary is printed after report generation.

---

## Limitations

- Supports both English and Chinese workflows; quality still depends on document layout/OCR quality.
- Analysis quality depends on document formatting and OCR quality.
- Incorrect parsing may affect extracted metrics.
- Generated reports are intended for informational purposes only.

---

## Notes

- PDF parsing is layout-aware with PyMuPDF when available, and falls back to `pdfplumber`/`PyPDF2`.
- Excel parsing requires `openpyxl`.
- API keys should always be configured using environment variables.
- Optional external search is disabled by default.
- For PDF documents, parser output includes `text`, `raw_text`, `cleaned_text`, `tables`, and `table_regions`.
- `table_regions` keeps 2D rows with page/bbox metadata, for example `{ "page": 10, "bbox": [x0, y0, x1, y1], "rows": [["Metric", "2025"], ["Revenue", "1000"]] }`.

### Execution Boundaries

- Financial metrics and `risk_score` are treated as internal ground truth.
- External evidence (RAG/MCP/Web) is supporting context and must not override core numeric metrics.
- Recommendation is rule-enforced in code (`BUY`/`HOLD`/`SELL`) rather than left to unconstrained LLM output.

### Current Workflow

```text
PDF/XLSX -> parser -> metric extraction -> risk scoring -> [Tavily MCP external search, if enabled] -> report -> reflection validation
```

---

### Embeddings and Vector Store

- This project supports BGE-based embeddings via `providers/embedding_provider_bge.py`. You can select the embedding locale via the environment variable `EMBED_LOCALE` (`en` or `zh`) or set a specific model with `EMBED_MODEL`.
- By default the repo falls back to a deterministic local stub embedder when BGE runtime is not available.
- The local `VectorStore` uses FAISS for efficient similarity search if `faiss` is installed; otherwise it falls back to an in-memory NumPy brute-force search. To enable FAISS install it in your environment (for example `pip install faiss-cpu`).
- Initial RAG indexing now includes both text chunks and structured table chunks (`chunk_type: table`) so table page context can be retrieved and cited.

---

## Checkpointing

During graph construction the skill writes a lightweight LangGraph checkpoint that records node names and edges for inspection. The file is written to:

```
workspace/cache/langgraph_checkpoint.sqlite
```

This checkpoint is intended for debugging and reproducibility inspection only; it does not serialize node callables.

---

## Architecture

See the architecture diagram: [ARCHITECTURE](docs/ARCHITECTURE.md)

---

## Preparing a Release (safe cleanup)

Before publishing to GitHub you may want to remove runtime caches and large local artifacts. A safe dry-run script is provided:

```bash
python scripts/prepare_release.py
```

To actually delete the suggested files, run:

```bash
python scripts/prepare_release.py --apply
```

The script will list candidate paths (dry-run) and ask for confirmation before deleting when `--apply` is used.

