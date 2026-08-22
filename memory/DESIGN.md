内存子系统设计（Memory System）

目标：为技能提供长期与短期记忆能力，支持查询、存储、持久化以及与反思（reflection）和RAG（检索增强生成）模块的集成。

组件：
- MemoryManager: 统一内存入口，负责添加、查询、按时间检索、持久化到磁盘（JSON）以及简单的关键词检索。提供一个轻量级接口，便于后续替换为向量数据库或外部向量服务。
- VectorStore（占位）: 将来用于 embedding 和高质量相似度搜索（当前用简单关键词匹配占位）。
- Retriever 接口（外部RAG适配器）：用于对接第三方检索引擎或自建向量服务。

数据模型（内存项）示例：
{
  "id": "uuid",
  "timestamp": 1690000000.0,
  "type": "observation|evidence|lesson|trace",
  "content": "文本内容",
  "metadata": { ... }
}

工作流程集成：
- 写入：技能或运行时事件通过 `MemoryManager.add()` 写入内存，并可选择立即持久化。
- 查询：RAG 接口会首先调用外部检索器（如果配置），然后回退到 MemoryManager.query() 用近期或关键词上下文补全提示。
- 反思：`ReflectionEngine` 接受 `MemoryManager` / `RAGTool` 的实例，能够在评估时拉取相关记忆并加入分析上下文。

迁移路径：
- 先用本地 JSON 存储与关键词检索实现快速迭代。
- 需要更强检索时，替换 VectorStore 为 Milvus/FAISS/Weaviate 并实现 Retriever 接口。

安全与保密：
- 存储文件位置默认在 `workspace/cache/memories.json`，可通过构造参数覆盖。
- 不在代码中记录敏感信息；如果需存储敏感数据，应该提供加密层或策略过滤。

说明：此设计偏向可迭代、低成本的实现，以便尽快联通反思与RAG功能，后续可替换检索/向量化子模块而不改动上层逻辑。
