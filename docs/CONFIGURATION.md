# 配置与目标机器部署清单

本文对应当前代码，集中说明必须配置、可选配置和未开放的能力。命令均在仓库根目录执行；密钥示例只是占位符，不能直接使用。

## 1. 部署前必须确认

- 建议使用 Python 3.11；发布检查要求 Python >= 3.11。当前开发机器没有可用 Python，尚未验证 Python 依赖安装、单元测试、OCR 或 Docling 运行。
- 基础依赖见 requirements.txt；其中固定版本仍需在目标机器确认可安装。不要把已有版本固定理解为已通过兼容性验收。
- 前端不需要 npm 安装或构建。Node.js 仅用于前端测试和可选 Tavily MCP。
- CLI 不依赖前端服务。资源紧张时不启动 server.py，且优先使用 native 解析、单任务处理。
- 正式模式会向 DeepSeek 发送研究材料相关内容；启用外部搜索还会向搜索服务发送查询。使用真实材料前确认数据授权和服务使用范围。
- 本系统提供待复核研究底稿，不是交易执行系统；配置齐全不代表分析正确或具备投资有效性。

## 2. 创建环境与最小演示

Windows PowerShell（无需激活虚拟环境）：

~~~powershell
py -3.11 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe main.py --input-file "examples/Quarterly financial statements Q1_2025.xlsx" --demo
~~~

Linux/macOS（先由管理员准备 Python 3.11 和 venv 支持）：

~~~sh
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python main.py --input-file "examples/Quarterly financial statements Q1_2025.xlsx" --demo
~~~

后续示例中的 python 应替换为上述虚拟环境解释器路径，或先激活该环境。演示模式不调用大模型 API，但不能通过正式交付校验；演示的待复核退出码不是安装失败。

## 3. 环境变量总表

代码不自动加载 .env。请在启动进程的终端、服务管理器或秘密管理系统中注入变量；只创建 .env 文件不会生效。Web 子任务继承服务启动时的环境，修改环境后需重启服务。

| 变量 | 默认值 | 何时配置 / 作用 |
| --- | --- | --- |
| DEEPSEEK_API_KEY | 无 | 正式模式必填；演示模式不需要 |
| LLM_MODEL | deepseek-chat | 默认模型，可由 CLI --model 覆盖；账户须有访问权限 |
| DEEPSEEK_RETRIES | 3 | LLM 请求重试配置，整数；见 providers/llm_provider.py |
| DEEPSEEK_TIMEOUT | 60 | 单次 HTTP 请求超时秒数，不是整个任务超时 |
| DEEPSEEK_BACKOFF_BASE | 1 | 重试退避基数，数值 |
| INPUT_FILE | 无 | 未传 --input-file 时的输入路径 |
| PDF_ENGINE | native | native 或 docling；仅影响 PDF |
| PDF_OCR | auto | auto、off 或 force；仅影响 PDF |
| PDF_OCR_LANGUAGE | chi_sim+eng | OCR 语言，对应语言数据必须已安装 |
| PDF_OCR_DPI | 200 | 100–300；native OCR 使用，Docling 适配器不消费此项 |
| TESSDATA_PREFIX | 系统环境 | Tesseract 语言数据所在 tessdata 目录，填写目标机器实际路径 |
| RESEARCH_UI_TOKEN | 启动时随机生成 | 可选固定工作台令牌；留空则读取启动输出中的随机令牌 |
| TAVILY_API_KEY | 无 | 仅在显式开启外部搜索时需要 |

不要设置不存在的开关：当前没有可配置的 BASE_URL 环境变量；DeepSeek 地址由 provider 构造参数决定。旧 ENABLE_TAVILY 不控制当前正式入口；旧 embedding 配置不是当前默认研究流程的前置条件。

正式模式示例（用真实密钥替换占位符，避免把密钥写入脚本、Git 或共享终端记录）：

~~~powershell
$env:DEEPSEEK_API_KEY = '<YOUR_PRIVATE_KEY>'
$env:LLM_MODEL = 'deepseek-chat'
python main.py --input-file 'D:/private/report.pdf' --output-dir workspace/runs
~~~

~~~sh
export DEEPSEEK_API_KEY='<YOUR_PRIVATE_KEY>'
export LLM_MODEL='deepseek-chat'
python main.py --input-file '/private/report.pdf' --output-dir workspace/runs
~~~

## 4. PDF / OCR / Docling 可选配置

### 原生 PDF 与 OCR

基础路径可使用 pdfplumber；推荐的逐页 native 路径使用 PyMuPDF，缺失时降级信息会记录到结果中。仅安装 native 增强依赖可以执行：

~~~sh
python -m pip install "PyMuPDF>=1.24,<2"
~~~

需要扫描件 OCR 时，另行安装系统 Tesseract 与 chi_sim、eng 语言数据。原生 PyMuPDF OCR 需要可发现的 tessdata；Docling 的 Tesseract CLI 还要求 tesseract 可执行文件在 PATH 中。用 tesseract --list-langs 核对语言，不能只安装 Python 包。

~~~powershell
$env:PDF_ENGINE = 'native'
$env:PDF_OCR = 'auto'
$env:PDF_OCR_LANGUAGE = 'chi_sim+eng'
$env:PDF_OCR_DPI = '200'
$env:TESSDATA_PREFIX = 'C:/REPLACE_WITH_ACTUAL_PATH/tessdata'
~~~

Linux/macOS 对应使用 export NAME='value'；路径必须改为实际目录。auto 按页面文字量、异常字符和图像覆盖情况决定是否 OCR；off 禁止 OCR；force 强制 OCR。当前 native 路径有 1000 页及单页 OCR 30 百万像素预算保护，不能通过提高 DPI 无限扩大工作量。

OCR 产生文本不等于恢复扫描表格结构。解析/OCR 警告会进入复核流程，不能通过改配置绕过证据校验。

### Docling（可选、较重）

~~~sh
python -m pip install -r requirements-parsing.txt
~~~

该文件安装 PyMuPDF 与 Docling；版本范围是候选兼容范围，不是已验证锁文件。安装后设置 PDF_ENGINE=docling；仍需配置 OCR 语言和系统依赖。首次使用可能下载模型，需预留网络、磁盘与内存，并确认下载和数据使用策略。目标机器验证后应保存实际依赖版本，例如 python -m pip freeze > workspace/validated-environment.txt，审查后再决定是否纳入版本管理。

Docling 输出及跨页表格仍需人工复核，不会自动替换默认引擎。目前没有启用多模态大模型自动识图；也没有可配置的自动视觉模型、因子训练或深度学习训练入口。

## 5. 可选工作台与资源限制

~~~sh
python server.py --port 8765 --data-dir workspace/web --workers 1
~~~

- 服务仅绑定 127.0.0.1，浏览器访问本机 8765 端口。将启动时显示的令牌填入页面；也可预先设置 RESEARCH_UI_TOKEN。令牌只在页面内存中保存，刷新后需重新填写。
- 所有 API 请求需 Bearer 令牌。正式上传还需在界面明确同意外部模型处理；服务进程必须已配置 DEEPSEEK_API_KEY。
- --workers 只接受 1 或 2，默认 1。队列活动任务容量为 8，任务超时为 900 秒：这两项目前是 server.py 的构造默认值，不是 CLI 或环境变量开关。
- 单文件上传上限为 20 MB，支持 PDF/XLSX，并有文件头和压缩包检查。不要将服务直接暴露公网，它没有多用户权限、TLS 或生产级租户隔离。
- 远程机器可经受控 SSH 隧道访问，保持两端相同端口，例如 ssh -N -L 8765:127.0.0.1:8765 user@server；当前 Host/Origin 校验不支持随意改变访问主机和端口。
- 上传和任务文件保存在 --data-dir；CLI 结果默认位于 workspace/runs/<run_id>/。没有自动清理策略，需管理员按授权与保留期限备份、清理，避免删除运行中任务。
- 停止服务不影响独立 CLI。直接打开 frontend/index.html 只用于本地 JSON 导入，不支持上传。页面预览需要服务端解析依赖。
- A2UI 为 v0.9 受限子集，结果接口返回完整 NDJSON；不是完整通用 A2UI 客户端或实时 token 流。上传和任务管理是固定页面逻辑。

## 6. 可选外部搜索

默认关闭。需要 Node.js/npm/npx、可访问 MCP 服务的网络和 TAVILY_API_KEY；服务启动定义位于 config/mcp.json。

~~~sh
python main.py --input-file '/private/report.pdf' --enable-external-search
~~~

Web 页面未提供该开关。开启前确认查询的数据授权、网络与费用；演示验收应不加此参数，避免额外外部依赖。

## 7. 目标机器验收与评测配置

~~~sh
python scripts/verify_release.py
node --check frontend/app.js
node --check frontend/a2ui.js
node tests/test_frontend.cjs
~~~

verify_release.py 检查 Python 版本、语法、基础依赖精确版本并运行 Python 单元测试；它不能代替真实 OCR、Docling、生产模型和浏览器人工验收。

解析对比评测步骤：

1. 复制 evaluation/manifest.template.json 到私有评测目录；其中只是占位内容，不是真实标注集。
2. 为每个样本填写 id、相对 manifest 所在目录的 file 路径、sha256，以及人工逐格抄录的 rows。page 为从 1 开始的页码；row 为字符串数组。
3. Windows 用 Get-FileHash -Algorithm SHA256 计算哈希并转小写；Linux 用 sha256sum，macOS 用 shasum -a 256。核对原文后才设置 reviewed=true。
4. 先验收 native，再安装可选依赖对比 Docling。不要把私有 PDF、标注或报告提交到公共仓库。

~~~sh
python scripts/benchmark_parsers.py workspace/benchmark/manifest.json --engines native --output workspace/benchmark/native.json
python scripts/benchmark_parsers.py workspace/benchmark/manifest.json --engines native docling --output workspace/benchmark/comparison.json
~~~

评测只衡量已标注表格行的精确匹配、定位可用性与耗时，不代表财务理解或投资收益。基准不会自动切换默认解析引擎。

CLI stdout 是 JSON，日志在 stderr；退出码 0=succeeded、2=needs_review、1=failed。消费结果时必须检查 result.json 中的状态与复核原因，而不是只看到报告文件就认为成功。--run-id（别名 --thread-id）可指定任务 ID，已存在 ID 不能重复使用。

## 8. 常见配置问题

| 现象 | 排查方向 |
| --- | --- |
| 正式任务提示缺少密钥 | 确认变量配置在启动进程所在终端；.env 不会自动加载 |
| OCR 缺少中文或不可用 | 核对 tessdata 实际路径、chi_sim/eng 数据，以及 Docling 所需 PATH |
| 安装提示版本不存在或冲突 | 保存错误、Python/平台版本，核对 requirements.txt；当前环境未验证可安装性，不要跳过验收 |
| 工作台返回 401/403 | 核对本次启动令牌、localhost/127.0.0.1 同端口访问及 Origin；不要取消鉴权 |
| 解析结束但 needs_review | 查看解析警告、证据、期间、单位和校验结果；这不必然是配置错误 |
| Docling 首次慢、超时或内存不足 | 核对模型下载；减少并发，先回退 native，必要时独立 CLI 分批运行 |
| 页面预览失败 | 核对 PyMuPDF、页码、原始 PDF 和当前任务令牌 |

## 9. 本次配置文档修改位置与原因

| 位置 | 修改原因 |
| --- | --- |
| docs/CONFIGURATION.md | 集中部署依赖、实际配置入口、隐私边界、资源限制与目标机验收步骤，避免依赖聊天记录 |
| README.md | 增加配置文档入口，便于克隆仓库后发现 |

此前功能升级的位置与原因另见 docs/A2UI_WORKBENCH.md、docs/PARSING_UPGRADE.md 和 docs/UPGRADE_BATCH_2.md。当前文档未宣称 Python/OCR/Docling 已通过本机测试。
