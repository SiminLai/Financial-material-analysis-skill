"use strict";
const element = id => document.getElementById(id);
const display = value => value === null || value === undefined ? "未知" : String(value);
let selection = 0;
function append(parent, tag, text) {
  const child = document.createElement(tag);
  child.textContent = text;
  parent.appendChild(child);
  return child;
}
function list(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 10000) throw new Error("结果条目结构不合法或过多。");
  return value;
}
function render(data) {
  element("results").hidden = true;
  if (!data || data.schema_version !== "research-1.0" || !["succeeded", "needs_review", "failed"].includes(data.status)) throw new Error("请选择本项目生成的 result.json。");
  element("run").textContent = display(data.run_id);
  element("status").textContent = display(data.status);
  element("mode").textContent = display(data.execution_mode);
  for (const id of ["issues", "facts", "rules", "evidence"]) element(id).replaceChildren();
  if (data.error) append(element("issues"), "li", display(data.error.type) + ": " + display(data.error.message));
  for (const issue of list(data.validation?.issues)) append(element("issues"), "li", display(issue.code) + " · " + display(issue.fact_id));
  if (!element("issues").childNodes.length) append(element("issues"), "li", "当前校验范围内没有阻断问题；不代表投资结论成立。");
  for (const fact of list(data.facts)) {
    const row = append(element("facts"), "tr", "");
    for (const value of [fact.metric, fact.value, display(fact.unit) + " / " + display(fact.currency), display(fact.period) + " / " + display(fact.scope), fact.validation_status, list(fact.evidence_refs).join(", ")]) append(row, "td", display(value));
  }
  for (const rule of list(data.risk?.rule_checks)) append(element("rules"), "li", display(rule.rule) + " · " + display(rule.status) + " · " + display(rule.reason));
  for (const item of list(data.evidence)) {
    const details = append(element("evidence"), "details", "");
    append(details, "summary", display(item.id) + " · 页 " + display(item.page) + " / 工作表 " + display(item.sheet));
    append(details, "pre", JSON.stringify(item, null, 2));
  }
  element("results").hidden = false;
}
element("file").addEventListener("change", async () => {
  const token = ++selection;
  element("results").hidden = true;
  element("message").className = "";
  const file = element("file").files[0];
  if (!file) { element("message").textContent = "尚未加载文件。"; return; }
  try {
    if (file.size > 20 * 1024 * 1024) throw new Error("文件超过 20 MB，请使用命令行查看。");
    const text = await file.text();
    if (token !== selection) return;
    render(JSON.parse(text));
    element("message").textContent = "已在本地加载，没有上传或调用模型。";
  } catch (error) {
    if (token !== selection) return;
    element("results").hidden = true;
    element("message").className = "error";
    element("message").textContent = error.message;
  }
});
