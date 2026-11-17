const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
class Element {
  constructor() { this.childNodes = []; this.textContent = ""; this.hidden = true; }
  appendChild(child) { this.childNodes.push(child); }
  replaceChildren() { this.childNodes = []; }
  addEventListener(name, handler) { this[name] = handler; }
}
const elements = new Map();
const context = vm.createContext({document: {
  getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
  createElement() { return new Element(); }
}});
const source = fs.readFileSync("frontend/app.js", "utf8");
vm.runInContext(source, context);
context.payload = {schema_version: "research-1.0", status: "needs_review", run_id: "<script>bad</script>", facts: [], evidence: []};
vm.runInContext("render(payload)", context);
assert.equal(elements.get("run").textContent, "<script>bad</script>");
assert.equal(elements.get("results").hidden, false);
assert.throws(() => vm.runInContext("render({})", context));
assert.equal(elements.get("results").hidden, true);
assert.throws(() => vm.runInContext("list({})", context));
assert.doesNotMatch(source, /innerHTML|fetch\(|XMLHttpRequest/);
(async () => {
  elements.get("file").files = [{size: 21 * 1024 * 1024}];
  await elements.get("file").change();
  assert.equal(elements.get("message").className, "error");
  elements.get("file").files = [{size: 2, text: async () => "xx"}];
  await elements.get("file").change();
  assert.equal(elements.get("results").hidden, true);
  console.log("PASS: safe rendering, invalid schema/array/JSON and oversized file rejection");
})().catch(error => { console.error(error); process.exitCode = 1; });
