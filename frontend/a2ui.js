"use strict";
(function (scope) {
  const catalog = "https://a2ui.org/specification/v0_9/catalogs/minimal/catalog.json";
  class Renderer {
    constructor(container, onAction) { this.container = container; this.onAction = onAction; this.surfaces = new Map(); }
    clear() { this.surfaces.clear(); this.container.replaceChildren(); }
    accept(message) {
      if (message.version !== "v0.9") throw new Error("不支持的 A2UI 版本");
      const names = ["createSurface", "updateComponents", "updateDataModel", "deleteSurface"].filter(name => Object.hasOwn(message, name));
      if (names.length !== 1) throw new Error("无效 A2UI 消息");
      const name = names[0], payload = message[name];
      if (!payload || typeof payload.surfaceId !== "string") throw new Error("缺少 surfaceId");
      const id = payload.surfaceId;
      if (name === "createSurface") {
        if (payload.catalogId !== catalog || this.surfaces.has(id) || this.surfaces.size >= 4) throw new Error("不支持的组件目录或重复界面");
        this.surfaces.set(id, {components: new Map(), data: {}});
        return;
      }
      const surface = this.surfaces.get(id);
      if (!surface) throw new Error("界面尚未创建");
      if (name === "deleteSurface") { this.surfaces.delete(id); this.container.replaceChildren(); return; }
      if (name === "updateDataModel") {
        if (payload.path && payload.path !== "/") throw new Error("当前组件集仅支持根数据更新");
        surface.data = payload.value ?? {};
      } else {
        if (!Array.isArray(payload.components) || payload.components.length > 1000) throw new Error("组件数量异常");
        for (const component of payload.components) {
          if (typeof component.id !== "string" || !["Text", "Column", "Row", "Button"].includes(component.component)) throw new Error("未授权组件");
          surface.components.set(component.id, component);
        }
        if (surface.components.size > 1000) throw new Error("组件数量超限");
      }
      if (surface.components.has("root")) this.container.replaceChildren(this.build(id, "root", new Set(), {count: 0}));
    }
    value(surface, value) {
      if (typeof value === "string") return value;
      if (!value || typeof value.path !== "string" || !value.path.startsWith("/")) throw new Error("无效数据绑定");
      let current = surface.data;
      for (const key of value.path.slice(1).split("/").map(part => part.replace(/~1/g, "/").replace(/~0/g, "~"))) {
        if (["__proto__", "constructor", "prototype"].includes(key)) throw new Error("不安全的数据路径");
        current = current && Object.hasOwn(current, key) ? current[key] : undefined;
      }
      return current === undefined || current === null ? "未知" : String(current);
    }
    build(surfaceId, id, ancestors, budget) {
      if (ancestors.has(id) || ancestors.size > 30 || ++budget.count > 2000) throw new Error("组件树循环或过深");
      const surface = this.surfaces.get(surfaceId), component = surface.components.get(id);
      if (!component) throw new Error("组件引用不存在");
      const next = new Set(ancestors); next.add(id);
      const type = component.component;
      const tag = type === "Text" ? ({h1: "h2", h2: "h2", h3: "h3"}[component.variant] || "p") : type === "Button" ? "button" : "div";
      const node = document.createElement(tag);
      node.className = "a2-" + type.toLowerCase();
      if (type === "Text") node.textContent = this.value(surface, component.text);
      else if (type === "Button") {
        node.className += " primary";
        node.type = "button";
        node.appendChild(this.build(surfaceId, component.child, next, budget));
        const event = component.action?.event;
        if (!event || event.name !== "download_result") throw new Error("未授权动作");
        node.addEventListener("click", () => this.onAction({version: "v0.9", action: {name: event.name, surfaceId,
          sourceComponentId: id, timestamp: new Date().toISOString(), context: {jobId: surfaceId}}}));
      } else {
        if (!Array.isArray(component.children)) throw new Error("仅支持显式子组件列表");
        for (const child of component.children) node.appendChild(this.build(surfaceId, child, next, budget));
      }
      return node;
    }
  }
  scope.ResearchA2UI = {Renderer, catalog};
})(globalThis);
