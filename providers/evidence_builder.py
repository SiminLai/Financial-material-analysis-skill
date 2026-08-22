from typing import List, Dict, Any
from reflection.evidence import Evidence
from reflection.evidence_store import EvidenceStore
try:
    import fitz
except Exception:
    fitz = None


class EvidenceBuilder:
    def __init__(self, store: EvidenceStore):
        self.store = store

    def from_text(self, text: str, source: str, page: int = None, meta: Dict[str, Any] = None) -> str:
        e_meta = meta or {"type": "text"}
        e = Evidence(id=None, content=text, source=source, page=page, meta=e_meta)
        return self.store.add(e.to_dict())

    def from_table_items(self, items: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for it in items:
            # items expected to have content, page, row, col, meta
            e = Evidence(
                id=None,
                content=it.get('content'),
                source=it.get('meta', {}).get('source', 'table'),
                page=it.get('meta', {}).get('page'),
                row=it.get('meta', {}).get('row'),
                col=it.get('meta', {}).get('col'),
                confidence=it.get('meta', {}).get('confidence', 0.9),
                meta=it.get('meta', {})
            )
            ids.append(self.store.add(e.to_dict()))
        return ids

    def from_rag_items(self, items: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for it in items:
            e = Evidence(
                id=it.get('id'),
                content=it.get('content') or it.get('text') or '',
                source=it.get('meta', {}).get('source', 'retriever'),
                page=it.get('meta', {}).get('page'),
                meta=it.get('meta', {})
            )
            ids.append(self.store.add(e.to_dict()))
        return ids
