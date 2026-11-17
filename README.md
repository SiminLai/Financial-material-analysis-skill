# Evidence-first Financial Research / 证据优先财报研究

当前正式入口是 main.py 或 runtime.runtime.analyze_document。
流程：PDF/XLSX → 解析 → 指标抽取 → 有条件派生 → 证据与口径检查 → 风险规则 → 研究底稿 → 交付校验。

## 运行

部署前请阅读 [配置与目标机器部署清单](docs/CONFIGURATION.md)，包括密钥、PDF/OCR、可选前端、资源限制及验收步骤。

    python -m pip install -r requirements.txt
    python main.py --input-file "examples/Quarterly financial statements Q1_2025.xlsx" --demo

正式调用需要 DEEPSEEK_API_KEY，可通过 --model 指定模型。输入材料会发送给模型服务，应事先确认数据授权。
演示模式不调用模型 API，不能通过正式交付门槛。外部搜索默认关闭。

stdout 为一个 JSON 结果，日志输出 stderr。退出码：0 成功、2 待复核、1 失败。
每次任务写入 workspace/runs/<run_id>/，result.json 是正式交付封装；独立报告文件不应绕过运行状态消费。
缺失、不明确或不可比较的数据保留待复核，不生成 BUY/HOLD/SELL。

## 可选前端

运行 python server.py 启动可选本机工作台，支持令牌鉴权、上传、任务管理和 A2UI v0.9 研究结果展示。
也可直接打开 frontend/index.html 导入本地结果，但不支持服务端上传。
服务器资源紧张时，不启动 server.py 即可；CLI 没有前端依赖。
详情见 frontend/README.md。

## 验收与修改记录

逐页 PDF/OCR、可选 Docling、人工标注评测与原文预览见 docs/PARSING_UPGRADE.md。
解析配置使用 PDF_ENGINE、PDF_OCR、PDF_OCR_LANGUAGE、PDF_OCR_DPI 环境变量；默认引擎尚未根据真实基准重新选型。

    python scripts/verify_release.py
    node tests/test_frontend.cjs

修改位置、修改原因、目标机器步骤及限制见 docs/UPGRADE_BATCH_2.md。
本机未执行 Python 测试。请在目标机器完成验证后再使用真实数据。
README_en.md、README_zh.md 及旧架构图为历史设计资料；与此入口说明冲突时以本文件和升级记录为准。

本项目辅助材料研究，不保证投资收益，不替代专业判断。公司身份、公告时点及投资有效性尚需单独验证。
