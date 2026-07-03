---
name: financial-report-analysis-skill
description: Analyze financial reports, earnings releases, and SEC filings. Use when users upload annual reports, quarterly reports, financial statements, or ask for financial ratio analysis, risk assessment, and executive summaries.
version: 1.0.2
author: LLLLLLL
tags:
  - finance
  - report
  - pdf
  - analysis
---

# Financial Report Analysis Skill

## Overview

This Skill automatically analyzes financial reports and earnings documents.

It extracts key financial metrics, evaluates financial health, identifies potential risks, and generates structured summaries for investors, researchers, and analysts.

Supported documents include:

- Annual Reports
- Quarterly Reports
- Earnings Releases
- Financial Statements


---

## When to Use

Activate this Skill when users:

- Upload a financial report PDF
- Ask for financial statement analysis
- Request key financial indicators
- Need company risk analysis
- Want an executive summary
- Ask for profitability, liquidity, leverage, or cash flow analysis

Typical keywords include:

- financial report
- annual report
- earnings release
- SEC filing
- balance sheet
- income statement
- cash flow
- financial analysis
- ratio analysis

---

## Workflow

1. Parse uploaded PDF/xlsx documents.
2. Extract structured financial metrics.
3. Validate extracted values.
4. Calculate financial indicators.
5. Identify financial risks.
6. Generate a comprehensive investment summary.

---

## Output

The generated report typically contains:

- Executive Summary
- Revenue Analysis
- Profitability Analysis
- Balance Sheet Analysis
- Cash Flow Analysis
- Financial Ratios
- Risk Assessment
- Overall Financial Health

---

## Example

### Input

Upload:

Texas Instruments 2025 Annual Report website.pdf

### Output

- Revenue Growth
- Net Income
- Cash Flow
- Debt Ratio
- Gross Margin
- Risk Analysis
- Investment Summary

---

## Project Structure

This Skill includes:

- providers/
- tools/
- validators/
- skills/
- state/

The workflow is executed through `main.py`.

---

## Limitations

- Best suited for English financial reports.
- Accuracy depends on document quality.
- Calculated metrics rely on extracted values from uploaded documents.