import os
import json
import time
import uuid
from typing import List, Dict, Any, Optional


class MemoryManager:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join("workspace", "cache", "memories.json")
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._memories: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self._memories = json.load(f)
            else:
                self._memories = []
        except Exception:
            self._memories = []

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._memories, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, content: str, type: str = "observation", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "type": type,
            "content": content,
            "metadata": metadata or {},
        }
        self._memories.append(item)
        self._save()
        return item

    def query(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Very small-footprint keyword scorer: counts token occurrences."""
        q = (query or "").lower().split()
        if not q:
            return self.recent(k)

        scored = []
        for item in self._memories:
            text = (item.get("content") or "").lower()
            score = 0
            for tok in q:
                score += text.count(tok)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:k]]

    def recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return sorted(self._memories, key=lambda x: x.get("timestamp", 0), reverse=True)[:n]

    def clear(self):
        self._memories = []
        self._save()

    def __len__(self):
        return len(self._memories)
