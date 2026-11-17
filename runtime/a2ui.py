CATALOG = "https://a2ui.org/specification/v0_9/catalogs/minimal/catalog.json"


def result_messages(result, surface_id):
    components = []
    children = []
    data = {}

    def text(identifier, content, variant="body"):
        children.append(identifier)
        data[identifier] = str(content)
        components.append({"id": identifier, "component": "Text",
                           "text": {"path": "/" + identifier}, "variant": variant})

    text("title", "研究结果 / " + result.get("status", "unknown"), "h2")
    text("mode", "执行模式：" + result.get("execution_mode", "unknown"))
    text("notice", "仅辅助材料研究，不构成投资建议。未知不等于低风险。")
    if result.get("error"):
        text("error", "执行错误：" + str(result["error"]))
    text("facts-heading", "财务事实", "h3")
    for index, fact in enumerate(result.get("facts", [])[:100]):
        value = fact.get("value")
        text("fact-" + str(index), " / ".join(str(item) for item in (
            fact.get("metric"), value if value is not None else "未知",
            fact.get("unit") or "单位未知", fact.get("period") or "期间未知",
            fact.get("validation_status"), ", ".join(fact.get("evidence_refs", [])))))
    text("review-heading", "待复核事项", "h3")
    issues = result.get("validation", {}).get("issues", [])
    if not issues:
        text("no-issues", "当前检查范围内无阻断问题；公司身份与公告时点仍需核实。")
    for index, issue in enumerate(issues[:150]):
        text("issue-" + str(index), str(issue.get("code")) + " · " + str(issue.get("fact_id", "")))
    text("evidence-heading", "证据摘录", "h3")
    for index, evidence in enumerate(result.get("evidence", [])[:100]):
        text("evidence-" + str(index), str(evidence.get("id")) + " · 页 " + str(evidence.get("page"))
             + " · 工作表 " + str(evidence.get("sheet")) + "\n" + str(evidence.get("content", ""))[:2000])
    children.append("download")
    components.extend([
        {"id": "download", "component": "Button", "child": "download-label", "variant": "primary",
         "action": {"event": {"name": "download_result", "context": {"jobId": surface_id}}}},
        {"id": "download-label", "component": "Text", "text": "下载完整研究结果"},
        {"id": "root", "component": "Column", "children": children},
    ])
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": surface_id, "catalogId": CATALOG}},
        {"version": "v0.9", "updateDataModel": {"surfaceId": surface_id, "path": "/", "value": data}},
        {"version": "v0.9", "updateComponents": {"surfaceId": surface_id, "components": components}},
    ]
