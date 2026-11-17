# 文档解析升级：目标机器验收前不切换默认引擎

## 修改位置与原因

| 位置 | 修改 | 原因 |
| --- | --- | --- |
| providers/pdf_provider.py / _request | 正式入口转到 document_pipeline | 保留旧私有函数用于兼容，正式调用不再整份文件静默回退 |
| providers/document_pipeline.py | 原生解析、逐页异常隔离、图片占比/文字质量检测、可配置 OCR | 避免只有页眉文字就漏掉扫描表格；记录失败而不掩盖 |
| providers/docling_provider.py | 可选 Docling 文档与表格适配 | 结构模型输出统一为页、块、表格、坐标；不冒充已验证准确 |
| requirements-parsing.txt | 可选依赖 | 不强迫轻量服务器安装重型模型 |
| graph/financial_graph.py | 解析警告进入交付校验 | 部分页读取失败不能被包装成完整报告 |
| tools/metric_extractor_tool.py、runtime/research.py | 传递表格区域坐标和解析引擎 | 支持从指标追踪回原页区域 |
| runtime/runtime.py | 保存 document.json、page_quality 和 document_meta | 保留可复核的解析产物和逐页质量信息 |
| scripts/benchmark_parsers.py、evaluation/manifest.template.json | 人工标注、源文件摘要、精确行匹配、耗时和版本报告 | 没有人工核验的标签不能作为准确率依据 |
| server.py、frontend/app.js | 鉴权 PDF 页图预览与证据页选择 | 避免把原始 PDF 直接作为不受控网页嵌入；不向模型发送图片 |
| tests/test_document_pipeline.py | 质量路由及评测逻辑测试 | 目标机器回归依据 |

## 运行方式

安装主 requirements 后，可选安装 requirements-parsing.txt。该文件是版本范围，不是已经验证的锁文件。
另需安装系统 Tesseract 和 chi_sim、eng 语言数据；PyMuPDF OCR 需正确配置 TESSDATA_PREFIX。
Docling 首次运行可能下载模型；离线部署应预先准备模型缓存，并记录实际版本与模型文件摘要。
本机不安装 Python，不声称已跑通这些依赖。Docling 适配参考官方 pipeline_options 和 docling-core 文档模型接口，兼容性须在目标版本验证。

PowerShell 示例：

    $env:PDF_ENGINE='native'
    $env:PDF_OCR='auto'
    $env:PDF_OCR_LANGUAGE='chi_sim+eng'
    $env:PDF_OCR_DPI='200'
    python main.py --input-file your-report.pdf --demo

PDF_ENGINE 可选 native/docling；PDF_OCR 可选 auto/off/force。默认 native，缺 PyMuPDF 时以带警告的 pdfplumber 路径读取，不伪装成 OCR 完成。
原生引擎自动 OCR 条件：文字少、替代字符比例高，或图片区域占比较大。它是保守启发式，不保证检测所有混合页。
OCR 数字和结构化模型输出默认需要人工复核。扫描表格不会因为 OCR 读到了字就被宣称恢复了单元格结构。
页旋转纠偏、跨页表格语义合并、置信度校准尚未实现；Docling 多页表格明确标记而不强行压平。

## 评测与默认引擎决策

复制 evaluation/manifest.template.json 建立真实评测清单；标注财报来源文件 SHA256、1-based 页码和人工抄录的完整行。
至少覆盖中文/英文、原生/扫描/混合、负数与百分比、多期表头、跨页表格。reviewed 必须人工确认，示例模板不可当作标签。

    python scripts/benchmark_parsers.py evaluation/manifest.json --engines native docling
    python scripts/verify_release.py

报告默认 workspace/benchmark/report.json。比较精确行匹配、定位、有无解析失败和耗时；峰值内存、金融口径准确性及扫描图质量另行人工验收。
没有实际样本结果之前，不更换默认引擎；本次没有伪造基准准确率或完成默认模型选型。

## 原文与多模态边界

Web 任务详情会提供有证据页码的下拉框，通过令牌保护的页图接口展示原页；最大长边约 1800 像素。
表格 bbox 已保存，前端当前是整页查看，不是自动高亮或单元格精确裁剪。
document.json 与页图构成疑难区域人工复核入口。自动视觉模型调用未启用：需明确模型、成本预算、隐私授权及基准后再接入。
没有把多模态生成结果自动写回事实。该阶段是安全预留，不声称完成了视觉模型纠错。

## 验证状态

本机仅执行 Node 语法/协议测试与 git diff --check；Python、OCR、Docling、图预览和真实财报准确率在目标机器检验。
