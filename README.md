# Financial Report Analysis Skill / 财务报告分析技能

Current pipeline / 当前流程:

`PDF/XLSX -> parser -> metric -> risk -> (optional browser/MCP) -> report -> reflection validation`

Boundaries / 边界约束:

- Metrics and `risk_score` are internal ground truth; external evidence is supporting-only.
- 指标与 `risk_score` 为内部真值，外部证据仅作辅助，不可覆盖核心数值。
- Missing critical values such as `debt_ratio` remain `None`; the skill does not invent default values.
- 当关键字段缺失、跨层冲突或证据不足时，`needs_review` 会被置为 `True`，并将推荐结果强制改为 `REVIEW`。
- Reflection exposes component-level scores and blockers rather than forcing a single aggregate score when evidence is incomplete.

Choose your preferred language:

选择你的首选语言：

- [English](README_en.md)
- [中文](README_zh.md)

See the system architecture diagram in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

免责声明 / Disclaimer

本 Skill 提供的财报分析、指标提取、风险评估及生成内容仅供参考，不构成任何投资、法律、审计或财务建议。用户应结合原始财务报告及专业人士意见独立判断，因使用本 Skill 输出而产生的任何决策或损失，开发者不承担任何责任。

The financial analysis, metric extraction, risk assessment, and generated content provided by this Skill are for informational purposes only and do not constitute investment, legal, audit, or financial advice. Users should independently verify all results against the original financial reports and consult qualified professionals where appropriate. The developers assume no liability for any decisions or losses arising from the use of this Skill.