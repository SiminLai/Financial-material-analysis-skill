# Financial Report Analysis Skill

A lightweight financial analysis skill built with LangGraph for parsing and analyzing financial documents. It supports both PDF and XLSX inputs, extracts structured financial metrics, performs explainable risk analysis, and generates comprehensive financial reports.

Optional MCP-based external evidence retrieval is supported and disabled by default.

---

## Features

- Parse financial documents from PDF and Excel (`.xlsx`) files
- Extract key financial metrics such as revenue, net profit, debt ratio, and cash flow
- Perform explainable financial risk analysis
- Generate structured financial analysis reports
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

---

## Limitations

- Best suited for English financial documents.
- Analysis quality depends on document formatting and OCR quality.
- Incorrect parsing may affect extracted metrics.
- Generated reports are intended for informational purposes only.

---

## Notes

- PDF parsing requires `pdfplumber` and `PyPDF2`.
- Excel parsing requires `openpyxl`.
- API keys should always be configured using environment variables.
- Optional external search is disabled by default.

---

## Checkpointing

During graph construction the skill writes a lightweight LangGraph checkpoint that records node names and edges for inspection. The file is written to:

```
workspace/cache/langgraph_checkpoint.json
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

