---
name: financial-report-analysis-skill
description: Analyze financial documents including annual reports, quarterly reports, earnings releases, financial statements, and investor presentations. Extract structured financial metrics, perform explainable financial risk analysis, and generate comprehensive financial reports. Supports PDF and XLSX inputs with optional MCP-based external evidence retrieval.
version: 1.0.3
author: LLLLLLL
tags:
  - finance
  - financial-analysis
  - report
  - pdf
  - xlsx
  - risk-analysis
  - langgraph
  - mcp
---

# Financial Report Analysis Skill

## Overview

Financial Report Analysis Skill is an automated financial document analysis workflow built on a modular architecture.

It parses uploaded financial documents, extracts structured financial metrics, performs explainable financial risk analysis, and generates comprehensive financial reports.

Supported document types include:

- Annual Reports
- Quarterly Reports
- Earnings Releases
- Financial Statements
- Investor Presentations
- Excel-based Financial Tables

Supported file formats:

- PDF (`.pdf`)
- Excel (`.xlsx`)

---

## When to Use

Use this Skill when users:

- Upload financial reports or financial statements
- Request financial document analysis
- Need extraction of key financial metrics
- Ask for financial ratio analysis
- Need company risk assessment
- Want executive summaries
- Ask for profitability, liquidity, leverage, or cash flow analysis

Typical keywords include:

- financial report
- annual report
- quarterly report
- earnings release
- SEC filing
- balance sheet
- income statement
- cash flow statement
- financial analysis
- financial ratio
- investment summary

---

## Workflow

The Skill executes the following workflow:

1. Parse uploaded PDF or XLSX documents.
2. Extract structured financial metrics using the LLM.
3. Validate extracted financial values.
4. Perform explainable financial risk analysis.
5. Optionally retrieve external evidence through MCP-enabled search when configured.
6. Generate a structured financial analysis report.

Workflow diagram:

```text
Document
    │
    ▼
Document Parser
    │
    ▼
Metric Extraction
    │
    ▼
Risk Detection
    │
    ▼
(Optional) External Evidence Retrieval
    │
    ▼
Report Generation
```

---

## External Evidence Retrieval

This Skill supports optional external evidence retrieval through MCP.

External search is:

- Disabled by default.
- Enabled only when explicitly configured by the user.
- Triggered only when external search is enabled and additional evidence is required during risk analysis.

When enabled, the following information may be sent to the configured search service:

- Company name
- Financial risk categories
- Risk score
- Financial search keywords

The Skill does **not** upload:

- Original PDF documents
- Original Excel files
- Complete document contents
- Full financial statements

---

## Output

The generated report typically contains:

- Executive Summary
- Revenue Analysis
- Profitability Analysis
- Balance Sheet Analysis
- Cash Flow Analysis
- Financial Ratio Analysis
- Risk Assessment
- Overall Financial Health
- Investment Summary

---

## Example

### Input

Upload:

```
Texas Instruments 2025 Annual Report.pdf
```

or

```
Quarterly Financial Statement.xlsx
```

### Output

Example report sections:

- Executive Summary
- Revenue Analysis
- Net Income Analysis
- Cash Flow Analysis
- Debt Ratio
- Financial Ratios
- Risk Assessment
- Overall Financial Health
- Investment Summary

---

## Project Structure

```
financial-report-analysis-skill/

├── graph/
├── providers/
├── tools/
├── skills/
├── state/
├── validators/
├── workflow/
├── config/
├── examples/
└── main.py
```

The workflow is implemented using LangGraph and executed through `main.py`.

---

## Limitations

- Best suited for English financial documents.
- Analysis quality depends on document formatting and text extraction quality.
- OCR quality may affect extracted financial values.
- Generated reports are intended for informational purposes and should not be considered professional investment advice.
- External evidence retrieval depends on user configuration and third-party service availability.

---

## Notes

- PDF processing requires PDF parsing dependencies.
- Excel processing requires `openpyxl`.
- API keys should be configured using environment variables.
- External search capability is optional and disabled by default.
- The Skill uses modular Providers, Tools, and LangGraph nodes to support future extension.