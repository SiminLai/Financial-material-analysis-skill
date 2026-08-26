# Financial Report Analysis Skill

一个面向本地运行的“证据优先”财务分析工作流，支持 PDF/XLSX 文档解析、结构化指标抽取、确定性风险评分、生成报告，以及在报告之后执行 reflection 校验。

这个仓库目前更像是一个本地研究/自动化技能，而不是一个容器化服务应用。因此在当前状态下，不需要额外编写 Dockerfile 或 CI 配置，除非后续准备做线上部署或发布流程。

---

## 它现在做了什么

- 解析 PDF 和 Excel 财务报表
- 保留 `raw_text`、`cleaned_text`、`table_regions` 等证据字段
- 抽取结构化指标，如 `company_name`、`revenue`、`net_profit`、`debt_ratio`、`cash_flow`
- 当表格证据存在时，优先使用 `table_regions` 中的结构化数据
- 执行确定性的风险评分，并在关键字段缺失时触发 review gate
- 构建本地向量索引，基于文本 chunk 和表格 chunk 进行检索
- 将 vector 数据落盘到 `workspace/cache/` 中
- 按 `thread_id` 创建独立的 LangGraph SQLite checkpoint
- 运行反思式校验，检查完整性、一致性、缺失字段和潜在冲突
- 外部证据仅作支持，不覆盖内部指标和风险判断

---

## 当前架构

```text
PDF/XLSX -> parser -> rag_index -> metric extraction -> risk scoring -> report -> reflection validation
```

关键说明：

- 当前实现是确定性状态图工作流，而不是单纯的 ReAct 或严格 plan-and-execute 代理。
- `rag_index` 是正常执行链路的一部分，会把文档分块写入 vector store。
- vector 文件默认写入：`workspace/cache/vector_index.npz` 和 `workspace/cache/vector_index.npz.meta.json`。
- checkpoint 按 `thread_id` 区分，避免不同任务串扰。
- 缺失关键字段（例如 `debt_ratio`）会保留为 `None`，不会被伪造成默认值。

---

## 支持的输入

- 年报
- 季报
- 财报发布稿
- 财务报表
- 投资者演示文稿
- Excel 财务表格

支持格式：

- `.pdf`
- `.xlsx`

---

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

从项目根目录运行：

```bash
python main.py --input-file "examples/your_report.pdf"
```

PowerShell：

```powershell
python main.py --input-file "examples\your_report.pdf"
```

可选环境变量：

```powershell
$env:EMBED_LOCALE = "zh"
$env:INPUT_FILE = "examples\your_report.pdf"
python main.py
```

---

## 可选外部搜索

默认关闭外部搜索。只有确实需要时才开启 Tavily：

```powershell
$env:ENABLE_TAVILY = "true"
$env:TAVILY_API_KEY = "your_api_key"
python main.py --input-file "examples\your_report.pdf"
```

外部搜索仅作为辅助证据，不能覆盖真实抽取指标和确定性风险值。

---

## 嵌入与向量缓存

- BGE embedding 由 `providers/embedding_provider_bge.py` 提供。
- `EMBED_LOCALE` 可选择 `en` 或 `zh`。
- `EMBED_MODEL` 可覆盖默认模型选择。
- 若当前环境没有 `FlagEmbedding`，系统会回退到本地确定性 stub embedder。
- vector 索引会写入 `workspace/cache/` 目录，便于本地检索与调试。

---

## Checkpoint

每次图执行可以按 `thread_id` 生成 SQLite 断点文件，例如：

```text
workspace/cache/langgraph_checkpoint_<thread_id>.sqlite
```

这是本地调试与并发隔离手段。不同线程会写入不同 checkpoint 文件，避免相互串扰。

---

## 当前状态说明

这个仓库当前是本地 Python 工作流，不是容器化服务程序，所以：

- 不需要 Dockerfile。
- 不需要 CI 配置。
- 只有当你准备做线上部署、自动发布、托管服务或持续集成检查时，才需要补 Docker / CI。

这能让项目更轻、更直接地保持调试和迭代效率。

---

## 边界与限制

- 缺失关键字段会保留为 `None`，而不是偷偷填默认值。
- 当字段缺失、跨层冲突或证据弱时会触发 `needs_review`。
- 最终推荐结果由代码规则约束，而不是由模型随意输出。
- 生成结果只用于信息参考，不构成投资建议或审计意见。

---

## 运行产物位置

```text
workspace/
  cache/
    evidence_store.json
    vector_index.npz
    vector_index.npz.meta.json
    langgraph_checkpoint_<thread_id>.sqlite
```

这些都是本地调试与检索用的产物，可以按需清理。

