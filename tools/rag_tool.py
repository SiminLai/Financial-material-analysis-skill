from typing import List, Dict, Any, Optional


class RAGTool:
    """RAG adapter that prefers a vector store search, then external retriever, then MemoryManager."""

    def __init__(self, memory_manager=None, external_retriever=None, vector_store=None):
        self.memory_manager = memory_manager
        self.external_retriever = external_retriever
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int = 5):
        results = []

        # 1) vector store
        if self.vector_store:
            try:
                vs = self.vector_store.search(query, k)
                if vs:
                    # normalize metadata shape to dict with 'content'
                    for item in vs:
                        if isinstance(item, dict):
                            results.append({"id": item.get("id"), "content": item.get("text"), "meta": item.get("meta")})
                        else:
                            results.append({"content": str(item)})
                    if len(results) >= k:
                        return results[:k]
            except Exception:
                pass

        # 2) external retriever (e.g., MCP tool)
        if self.external_retriever:
            try:
                ext = None
                # external retriever might be asynchronous or synchronous with different interfaces
                if hasattr(self.external_retriever, "search"):
                    ext = self.external_retriever.search(query, k)
                elif hasattr(self.external_retriever, "call_mcp"):
                    ext = self.external_retriever.call_mcp(query)
                if ext:
                    for e in ext:
                        results.append({"content": e.get("text") if isinstance(e, dict) else str(e)})
                    if len(results) >= k:
                        return results[:k]
            except Exception:
                pass

        # 3) fallback to MemoryManager keyword query
        if self.memory_manager:
            try:
                mem = self.memory_manager.query(query, k)
                for m in mem:
                    results.append({"id": m.get("id"), "content": m.get("content"), "meta": m.get("metadata")})
            except Exception:
                pass

        # dedupe by content
        out = []
        seen = set()
        for r in results:
            c = (r.get("content") or "") if isinstance(r, dict) else str(r)
            if c in seen:
                continue
            seen.add(c)
            out.append(r)
            if len(out) >= k:
                break

        return out
