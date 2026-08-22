# Financial Report Analysis Skill

一个基于 LangGraph 构建的金融报告分析 Skill，可自动解析和分析财务文档，支持 PDF 与 XLSX 文件，提取关键财务指标，进行可解释的风险分析，并生成结构化财务分析报告。

支持可选的 MCP 外部搜索能力，默认关闭。

---

## 功能特点

- 支持 PDF 和 Excel（`.xlsx`）财务文档解析
- 自动提取收入、净利润、资产负债率、现金流等关键财务指标
- 提供可解释的财务风险分析
- 自动生成结构化财务分析报告
- 支持统一的多格式文档解析
- 基于 LangGraph 构建工作流
- 支持可选 MCP 外部搜索（默认关闭）

---

## 支持的文档类型

包括但不限于：

- 年报（Annual Report）
- 季报（Quarterly Report）
- 财报发布（Earnings Release）
- 财务报表（Financial Statement）
- 投资者演示文稿（Investor Presentation）
- Excel 财务数据表

支持格式：

- `.pdf`
- `.xlsx`

---

## 项目结构

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

## 安装

安装依赖：

```bash
pip install -r requirements.txt
```

---

## 配置

### 配置 DeepSeek API

Linux/macOS：

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
```

---

### （可选）开启 MCP 外部搜索

默认情况下，外部搜索关闭。

如需启用 Tavily 搜索，请配置：

Linux/macOS：

```bash
export ENABLE_TAVILY=true
export TAVILY_API_KEY="your_api_key"
```

Windows PowerShell：

```powershell
$env:ENABLE_TAVILY="true"
$env:TAVILY_API_KEY="your_api_key"
```

开启后，系统可能向搜索服务发送以下信息：

- 公司名称
- 风险评分
- 风险因素
- 财务搜索关键词

**不会发送：**

- 原始 PDF 文件
- 原始 Excel 文件
- 完整财务报告内容

---

## 使用方法

在项目根目录运行：

```bash
python main.py
```

默认情况下：

- 不开启外部搜索
- 仅基于本地文档完成分析

---

## 局限性

- 更适用于英文财务文档。
- 分析质量依赖于文档排版和 OCR 质量。
- 文档解析错误会影响最终分析结果。
- 生成结果仅供参考，不构成投资建议。

---

## 说明

- PDF 解析依赖 `pdfplumber` 和 `PyPDF2`。
- Excel 解析依赖 `openpyxl`。
- 所有 API Key 建议通过环境变量配置。
- 外部搜索功能默认关闭，需要用户主动开启。

---

## 检查点（Checkpoint）

在图构建阶段，系统会写入一个轻量级的 LangGraph 检查点文件（记录节点名称和边），用于调试和检查：

```
workspace/cache/langgraph_checkpoint.json
```

该文件仅用于检查和可重复性验证，不会序列化函数调用体。

---

## 架构图

查看系统架构图： [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

