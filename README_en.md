# Financial Report Analysis Skill

A lightweight financial analysis skill for parsing and analyzing financial documents. It supports both `PDF` and `XLSX` inputs, extracts structured metrics, evaluates risk, and generates grounded summary reports.

## Features

- Parse financial documents from PDF and Excel (`.xlsx`) files
- Extract key financial metrics such as revenue, net profit, debt ratio, and cash flow
- Perform deterministic risk scoring and explainable risk analysis
- Generate a structured investment summary with recommendations
- Unified document parser for multi-format input handling

## Supported Inputs

- Annual reports
- Quarterly reports
- Earnings releases
- Financial statements
- Investor presentations
- Excel-based financial tables

## Project Structure

- `main.py` - example entry point and workflow wiring
- `providers/` - data providers for PDF and Excel
- `tools/` - parsing, metric extraction, risk detection, and report generation tools
- `skills/` - skill wrapper and execution logic
- `state/` - workflow state container
- `validators/` - schema validation helpers
- `workflow/` - workflow orchestration
- `examples(pdf)/` - sample input documents

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

The skill uses a DeepSeek REST client in `providers/llm_provider.py`.
You can configure the API key by setting the environment variable:

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

On Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY = "your_api_key"
```

## Usage

Run the skill from the repository root:

```bash
python main.py
```

The `main.py` example currently invokes the skill against a sample file path. You can change the file path to any supported PDF or XLSX document.

## Example

```python
from providers.llm_provider import LLMProvider
from providers.pdf_provider import PDFProvider
from providers.excel_provider import ExcelProvider

from tools.pdf_parser_tool import PDFParserTool
from tools.excel_parser_tool import ExcelParserTool
from tools.document_parser_tool import DocumentParserTool
from tools.metric_extractor_tool import MetricExtractorTool
from tools.risk_detection_tool import RiskDetectionTool
from tools.report_generator_tool import ReportGeneratorTool

from workflow.financial_workflow import FinancialWorkflow
from skills.financial_analysis_skill import FinancialAnalysisSkill

llm_provider = LLMProvider("deepseek-v4-flash")
pdf_provider = PDFProvider()
excel_provider = ExcelProvider()

workflow = FinancialWorkflow(
    tools={
        "parser": DocumentParserTool(PDFParserTool(pdf_provider), ExcelParserTool(excel_provider)),
        "metric": MetricExtractorTool(llm_provider),
        "risk": RiskDetectionTool(llm_provider),
        "report": ReportGeneratorTool(llm_provider),
    }
)

skill = FinancialAnalysisSkill(workflow)
result = skill.invoke("examples(pdf)/Quarterly financial statements Q1_2025.xlsx")
print(result)
```

## Limitations

- Best suited for English financial documents
- Extraction quality depends on document formatting and OCR/text quality
- Metrics are derived from extracted text and tables, so errors in parsing affect results

## Notes

- If using Excel input, install `openpyxl`
- If using PDF input, install `pdfplumber` or `PyPDF2`
- Adjust `providers/llm_provider.py` if you need a different LLM endpoint or model
