const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
class Element {
  constructor() { this.children = []; this.textContent = ""; this.listeners = {}; }
  appendChild(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
}
const context = vm.createContext({document: {createElement() { return new Element(); }}, console});
vm.runInContext(fs.readFileSync("frontend/a2ui.js", "utf8"), context);
const container = new Element(); let action;
const renderer = new context.ResearchA2UI.Renderer(container, event => { action = event; });
const send = body => renderer.accept({version: "v0.9", ...body});
send({createSurface: {surfaceId: "test", catalogId: context.ResearchA2UI.catalog}});
send({updateDataModel: {surfaceId: "test", value: {name: "<script>alert(1)</script>"}}});
send({updateComponents: {surfaceId: "test", components: [
  {id: "root", component: "Column", children: ["title", "download"]},
  {id: "title", component: "Text", text: {path: "/name"}},
  {id: "download", component: "Button", child: "label", action: {event: {name: "download_result"}}},
  {id: "label", component: "Text", text: "Download"}
]}});
assert.equal(container.children[0].children[0].textContent, "<script>alert(1)</script>");
container.children[0].children[1].listeners.click();
assert.equal(action.version, "v0.9"); assert.equal(action.action.context.jobId, "test");
send({updateDataModel: {surfaceId: "test", value: {name: "Updated"}}});
assert.equal(container.children[0].children[0].textContent, "Updated");
assert.throws(() => renderer.accept({version: "v1.0", deleteSurface: {surfaceId: "test"}}));
assert.throws(() => send({createSurface: {surfaceId: "test", catalogId: context.ResearchA2UI.catalog}}));
assert.throws(() => send({updateComponents: {surfaceId: "test", components: [{id: "bad", component: "Script"}]}}));
assert.throws(() => send({updateComponents: {surfaceId: "test", components: [{id: "root", component: "Column", children: ["root"]}]}}));
send({deleteSurface: {surfaceId: "test"}}); assert.equal(container.children.length, 0);
assert.doesNotMatch(fs.readFileSync("frontend/a2ui.js", "utf8"), /innerHTML|eval\(/);
console.log("PASS A2UI: data binding, incremental update, text safety, actions, catalog/version rejection, cycle rejection, deletion");
const html = fs.readFileSync("frontend/index.html", "utf8");
const app = fs.readFileSync("frontend/app.js", "utf8");
const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map(match => match[1]));
for (const match of app.matchAll(/byId\("([^"]+)"\)/g)) assert.ok(ids.has(match[1]), "Missing DOM element: " + match[1]);
assert.doesNotMatch(app, /innerHTML|localStorage/);
console.log("PASS app: static DOM references and token persistence guard");
