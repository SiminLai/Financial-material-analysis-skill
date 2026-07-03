# 财务报告分析技能

一个用于解析和分析财务文档的轻量级技能。支持 `PDF` 和 `XLSX` 输入，提取结构化指标，评估风险，并生成落地的摘要报告。

## 功能

- 从 PDF 和 Excel (`.xlsx`) 文档解析财务内容
- 提取关键财务指标，如收入、净利润、资产负债率和现金流
- 执行确定性风险评分并生成可解释的风险分析
- 生成结构化投资摘要并给出建议
- 提供统一的文档解析器，支持多格式输入处理

## 支持输入

- 年度报告
- 季度报告
- 财报发布
- 财务报表
- 投资者演示材料
- 基于 Excel 的财务表格

## 项目结构

- `main.py` - 示例入口与工作流连接
- `providers/` - PDF 和 Excel 数据提供者
- `tools/` - 解析、指标提取、风险检测、报告生成工具
- `skills/` - 技能包装和执行逻辑
- `state/` - 工作流状态容器
- `validators/` - 模式验证辅助
- `workflow/` - 工作流编排
- `examples(pdf)/` - 示例输入文档

## 安装

```bash
pip install -r requirements.txt
```

## 配置

此技能通过 `providers/llm_provider.py` 使用 DeepSeek REST 客户端。
可以通过设置环境变量来配置 API Key：

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

在 Windows PowerShell 中：

```powershell
$env:DEEPSEEK_API_KEY = "your_api_key"
```

## 使用方法

从仓库根目录运行技能：

```bash
python main.py
```

`main.py` 示例当前使用样例文件路径调用技能。你可以将路径替换为任何支持的 PDF 或 XLSX 文档。

## 示例

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

## 限制

- 主要适用于英文财务文档
- 提取质量依赖于文档格式和 OCR / 文本质量
- 指标来源于提取的文本和表格，因此解析错误会影响结果

## 说明

- 如果使用 Excel 输入，请安装 `openpyxl`
- 如果使用 PDF 输入，请安装 `pdfplumber` 或 `PyPDF2`
- 如需使用不同 LLM 端点或模型，可调整 `providers/llm_provider.py`
