from typing import Dict, Any, List, Optional
import uuid
import json
import os


class EvidenceStore:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join("workspace", "cache", "evidence_store.json")
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._store = {k: v for k, v in data.items()}
            else:
                self._store = {}
        except Exception:
            self._store = {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, evidence: Dict[str, Any]) -> str:
        eid = evidence.get('id') or str(uuid.uuid4())
        evidence['id'] = eid
        self._store[eid] = evidence
        self._save()
        return eid

    def add_many(self, items: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for it in items:
            ids.append(self.add(it))
        return ids

    def get(self, eid: str) -> Optional[Dict[str, Any]]:
        return self._store.get(eid)

    def get_many(self, eids: List[str]) -> List[Dict[str, Any]]:
        return [self._store[e] for e in eids if e in self._store]

    def recent(self, n: int = 10) -> List[Dict[str, Any]]:
        items = list(self._store.values())
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return items[:n]
