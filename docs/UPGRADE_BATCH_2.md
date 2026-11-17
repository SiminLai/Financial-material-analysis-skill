# 第二批升级与验收记录

日期：2026-11-17。当前机器不安装 Python；Python 测试必须在目标机器执行。

## 修改位置与原因

| 文件 / 函数 | 本批修改 | 原因 |
| --- | --- | --- |
| runtime/research.py / research_report | 深拷贝事实与风险结果 | 防止报告与原始状态共享对象，导致篡改检查失效 |
| runtime/research.py / finalize_research | 检查必需指标、数值有效性、验证状态、空证据、重复 ID、规则一致性 | 不能仅依赖上游 issues 列表宣布成功 |
| runtime/runtime.py / analyze_document | 每次调用使用独立 logger；落盘失败清空成功路径、更新失败状态并尽力写入失败标记 | 防止重复任务混用日志，以及交付部分产物后误报成功 |
| frontend/index.html、styles.css、app.js | 新增独立本地只读查看器 | 不引入后台进程、模型调用或上传；服务器可以完全不部署前端 |
| tests/test_frontend.cjs | 无依赖 Node DOM 替身测试 | 检查文本安全渲染、错误格式、JSON 与文件上限处理；不等于真实浏览器验收 |
| tests/test_research_delivery.py | 新增交付门槛、抽取安全、派生前提、任务隔离及写入失败测试 | 提供目标机器可执行的回归依据 |
| scripts/verify_release.py | 语法预检、依赖版本核对、完整 unittest 执行 | 提供跨机器统一验收入口，不自动安装软件或调用付费 API |
| .gitignore | 忽略 .tools | 排除上一轮未完成的本地环境下载，不删除用户文件 |
| README.md、SKILL.md | 对齐正式入口、退出码、演示模式和证据边界 | 避免宿主继续按旧 BUY/HOLD/SELL 或默认缓存逻辑调用 |

## 本机验证结果

- node --check frontend/app.js：通过。
- node tests/test_frontend.cjs：通过，覆盖安全文本渲染、错误 schema、数组、JSON 和超限文件。
- git diff --check：通过（仅有 Windows 换行转换提示）。
- Python 测试及真实浏览器视觉检查：未运行，留给目标机器验收。

## 目标机器验收

从仓库根目录执行，建议使用独立 Python 3.11 虚拟环境：

    python -m venv .venv

Windows 使用 .venv\Scripts\python.exe；Linux/macOS 使用 .venv/bin/python 替换后面的 python。

    python -m pip install -r requirements.txt
    python scripts/verify_release.py

依赖文件沿用仓库原有版本，本机没有验证这些版本能否安装；安装失败请保留 pip 输出，不要默默换版本后当作同一基线。
测试不应需要真实 API 密钥。测试里的合格数据是人工构造夹具，不代表真实财报抽取准确率。

可选前端检查（需要 Node）：

    node --check frontend/app.js
    node tests/test_frontend.cjs

离线流程冒烟测试（会解析真实样例，模型使用显式演示模式）：

    python main.py --input-file "examples/Quarterly financial statements Q1_2025.xlsx" --demo --run-id acceptance-demo

预期 stdout 为一个 JSON，execution_mode 为 demo，status 为 needs_review，退出码 2。
退出码 0 表示通过数值/证据规则门槛；1 表示执行失败；2 表示待复核。运行 ID 不可重复使用。
查看 workspace/runs/acceptance-demo/result.json，并用 frontend/index.html 打开此文件。
人工检查中文、窄屏、长证据展开、失败结果、空字段和恶意 HTML 字符串均以普通文本显示。

正式调用需要 DEEPSEEK_API_KEY，模型通过 --model 指定；该步骤有网络和费用，不属于离线验收。
CLI 不读取前端、不启动 HTTP 服务；不部署 frontend 不影响分析任务。

## 当前边界

- 未执行 Python 测试、真实模型分析或真实浏览器视觉验收；不能将本批视为生产认证。
- 原有表格抽取仍较保守，多列/重复指标可能拒绝选择；期间、单位、口径未知时应待复核。
- 本批没有实现多期间自动比较、人工确认后发布、因子训练或回测。
- 默认正式入口关闭向量检索和 checkpoint；保留的旧模块不是正式执行路径。
- succeeded 仅覆盖数值证据及规则检查，不覆盖公司身份、公告时点或投资价值。
- 存储完全不可写时只能返回失败，无法保证磁盘上已有部分文件同步更新；以调用返回状态及完整 result.json 为准，勿单独消费 report.json。
