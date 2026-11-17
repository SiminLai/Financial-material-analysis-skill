"use strict";
const byId = id => document.getElementById(id);
const statusLabels = {queued: "排队中", running: "分析中", succeeded: "校验通过", needs_review: "待复核", failed: "失败", interrupted: "已中断"};
let jobs = [], selectedFile = null, connected = false, busy = false, timer = null, detailSequence = 0, imported = null;
let sourceJob = null, sourceUrl = null, sourceRequest = 0;
const renderer = new ResearchA2UI.Renderer(byId("surface"), async event => {
  if (event.action.name !== "download_result") return;
  try {
    const result = event.action.surfaceId === "local" ? imported : await api("/api/jobs/" + event.action.surfaceId + "/result");
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], {type: "application/json"}));
    const link = document.createElement("a"); link.href = url; link.download = "result.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { notify(error.message, true); }
});
function notify(text, error = false) { byId("message").textContent = text; byId("message").className = error ? "error" : ""; }
function append(parent, tag, text, className = "") { const node = document.createElement(tag); node.textContent = text; node.className = className; parent.appendChild(node); return node; }
async function api(path, options = {}, ndjson = false) {
  if (location.protocol === "file:") throw new Error("请通过 python server.py 启动页面；直接打开文件仅支持本地结果导入。");
  const response = await fetch(path, {...options, headers: {...options.headers, Authorization: "Bearer " + byId("token").value.trim()}, signal: AbortSignal.timeout(45000)});
  if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(payload.error || "请求失败 " + response.status); }
  return ndjson ? response.text() : response.json();
}
function updateSubmit() { byId("submit").disabled = !connected || !selectedFile || busy || (byId("mode").value === "production" && !byId("consent").checked); }
function renderJobs() {
  for (const [key, count] of Object.entries({all: jobs.length, active: jobs.filter(job => ["queued", "running"].includes(job.status)).length, review: jobs.filter(job => job.status === "needs_review").length, done: jobs.filter(job => job.status === "succeeded").length})) byId("count-" + key).textContent = count;
  const query = byId("search").value.toLowerCase(), filter = byId("filter").value;
  const visible = jobs.filter(job => job.filename.toLowerCase().includes(query) && (filter === "all" || (filter === "active" ? ["queued", "running"].includes(job.status) : filter === "failed" ? ["failed", "interrupted"].includes(job.status) : job.status === filter)));
  byId("jobs").replaceChildren(); byId("empty").hidden = visible.length > 0;
  for (const job of visible) {
    const row = append(byId("jobs"), "tr", ""); const cell = append(row, "td", "");
    append(cell, "span", job.filename, "file-name"); append(cell, "div", (job.size / 1024).toFixed(1) + " KB · " + (job.mode === "demo" ? "演示" : "正式"), "file-meta");
    append(append(row, "td", ""), "span", statusLabels[job.status] || job.status, "badge " + job.status);
    append(row, "td", new Date(job.created_at).toLocaleString("zh-CN", {month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"}));
    const button = append(append(row, "td", ""), "button", "查看 →", "text-button");
    button.disabled = ["queued", "running"].includes(job.status);
    button.addEventListener("click", () => openJob(job));
  }
}
async function refresh() {
  clearTimeout(timer);
  try {
    const data = await api("/api/jobs"); if (!Array.isArray(data.jobs)) throw new Error("任务列表格式异常");
    jobs = data.jobs; connected = true; renderJobs();
    byId("connection-state").textContent = "分析服务已连接"; byId("connection-dot").className = "dot";
  } catch (error) { connected = false; byId("connection-state").textContent = "未连接 / 连接中断"; byId("connection-dot").className = "dot offline"; notify(error.message, true); }
  updateSubmit();
  if (connected) timer = setTimeout(refresh, document.hidden ? 15000 : 5000);
}
async function openJob(job) {
  const sequence = ++detailSequence;
  sourceRequest++; sourceJob = null; byId('source-panel').hidden = true; byId('source-image').hidden = true;
  try {
    const text = await api("/api/jobs/" + job.id + "/ui", {}, true);
    if (sequence !== detailSequence) return;
    renderer.clear();
    for (const line of text.split("\n").filter(line => line.trim())) renderer.accept(JSON.parse(line));
    byId("detail-title").textContent = job.filename; byId("detail").hidden = false; byId("detail").scrollIntoView({behavior: "smooth", block: "start"});
    if (/\.pdf$/i.test(job.filename)) {
      const result = await api('/api/jobs/' + job.id + '/result');
      if (sequence !== detailSequence) return;
      const pages = [...new Set((result.evidence || []).map(item => item.page).filter(page => Number.isInteger(page) && page > 0))];
      if (!pages.length && result.document_meta?.pages) pages.push(1);
      byId('source-page').replaceChildren();
      for (const page of pages.sort((first, second) => first - second)) {
        const option = append(byId('source-page'), 'option', '第 ' + page + ' 页'); option.value = page;
      }
      sourceJob = job.id; byId('source-panel').hidden = !pages.length;
    }
  } catch (error) { if (sequence === detailSequence) { renderer.clear(); notify(error.message, true); } }
}
function selectFile(file) {
  selectedFile = null;
  if (!file) return updateSubmit();
  if (!/\.(pdf|xlsx)$/i.test(file.name) || file.size > 20 * 1024 * 1024 || !file.size) { notify("请选择不超过 20 MB 的 PDF 或 XLSX 文件。", true); byId("file-label").textContent = "拖拽文件到这里"; updateSubmit(); return; }
  selectedFile = file; byId("file-label").textContent = file.name; updateSubmit();
}
byId("submit").addEventListener("click", async () => {
  if (byId("submit").disabled) return;
  busy = true; updateSubmit(); notify("正在上传文件，请勿重复提交…");
  try {
    await api("/api/jobs", {method: "POST", headers: {"Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(selectedFile.name), "X-Analysis-Mode": byId("mode").value, "X-Data-Consent": byId("consent").checked ? "yes" : "no"}, body: selectedFile});
    selectedFile = null; byId("document").value = ""; byId("file-label").textContent = "拖拽文件到这里"; notify("文件已接收，任务已进入队列。"); await refresh();
  } catch (error) { notify(error.message + "；如请求超时，请先刷新列表确认是否已创建任务。", true); }
  finally { busy = false; updateSubmit(); }
});
byId("document").addEventListener("change", event => selectFile(event.target.files[0]));
for (const name of ["dragover", "dragleave", "drop"]) byId("dropzone").addEventListener(name, event => { event.preventDefault(); byId("dropzone").classList.toggle("drag", name === "dragover"); if (name === "drop") selectFile(event.dataTransfer.files[0]); });
byId("connect").addEventListener("click", refresh); byId("refresh").addEventListener("click", refresh);
byId("search").addEventListener("input", renderJobs); byId("filter").addEventListener("change", renderJobs);
byId("mode").addEventListener("change", updateSubmit); byId("consent").addEventListener("change", updateSubmit);
byId("token").addEventListener("input", () => { connected = false; clearTimeout(timer); byId("connection-state").textContent = "令牌已修改，请重新连接"; byId("connection-dot").className = "dot offline"; updateSubmit(); });
byId("upload-focus").addEventListener("click", () => byId("document").click());
byId("close-detail").addEventListener("click", () => { detailSequence++; byId("detail").hidden = true; });
byId('show-source').addEventListener('click', async () => {
  const request = ++sourceRequest;
  if (!sourceJob) return;
  byId('source-image').hidden = true;
  try {
    const response = await fetch('/api/jobs/' + sourceJob + '/pages/' + byId('source-page').value,
      {headers: {Authorization: 'Bearer ' + byId('token').value.trim()}, signal: AbortSignal.timeout(30000)});
    if (!response.ok) throw new Error((await response.json()).error || '原文预览失败');
    const blob = await response.blob(); if (request !== sourceRequest) return;
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    sourceUrl = URL.createObjectURL(blob); byId('source-image').src = sourceUrl; byId('source-image').hidden = false;
  } catch (error) { if (request === sourceRequest) notify(error.message, true); }
});
for (const [id, filter] of [["all-nav", "all"], ["review-nav", "needs_review"]]) byId(id).addEventListener("click", () => { byId("filter").value = filter; renderJobs(); byId("all-nav").classList.toggle("active", filter === "all"); byId("review-nav").classList.toggle("active", filter !== "all"); });
byId("result-file").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file) return;
  const sequence = ++detailSequence;
  try {
    if (file.size > 20 * 1024 * 1024) throw new Error("结果文件超过 20 MB");
    sourceRequest++; sourceJob = null; byId('source-panel').hidden = true;
    const result = JSON.parse(await file.text());
    if (sequence !== detailSequence) return;
    if (result.schema_version !== "research-1.0" || !["succeeded", "needs_review", "failed"].includes(result.status)) throw new Error("结果格式不支持");
    imported = result; renderer.clear();
    renderer.accept({version: "v0.9", createSurface: {surfaceId: "local", catalogId: ResearchA2UI.catalog}});
    renderer.accept({version: "v0.9", updateComponents: {surfaceId: "local", components: [
      {id: "root", component: "Column", children: ["heading", "content", "download"]},
      {id: "heading", component: "Text", text: "本地结果 · " + result.status, variant: "h2"},
      {id: "content", component: "Text", text: JSON.stringify(result, null, 2).slice(0, 100000)},
      {id: "download", component: "Button", child: "label", action: {event: {name: "download_result"}}},
      {id: "label", component: "Text", text: "下载完整结果"}
    ]}});
    byId("detail-title").textContent = file.name; byId("detail").hidden = false; notify("本地结果已加载，未上传。");
  } catch (error) { renderer.clear(); notify(error.message, true); }
});
