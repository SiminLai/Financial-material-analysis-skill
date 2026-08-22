import os
import json
import numpy as np
from typing import List, Dict, Any, Optional

try:
    import faiss
    _HAS_FAISS = True
except Exception:
    faiss = None
    _HAS_FAISS = False


class VectorStore:
    def __init__(self, embedding_provider, dim: int = 128, index_path: Optional[str] = None):
        self.embedder = embedding_provider
        self.dim = dim
        self.index_path = index_path or os.path.join("workspace", "cache", "vector_index.npz")
        self._metadatas: List[Dict[str, Any]] = []
        self._vectors: Optional[np.ndarray] = None
        self._faiss_index = None
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    def add_documents(self, docs: List[Dict[str, Any]]):
        """Add documents: each doc must have `id` and `text` and optional `meta`."""
        texts = [d["text"] for d in docs]
        vecs = self.embedder.embed(texts)

        if self._vectors is None:
            self._vectors = vecs
        else:
            self._vectors = np.vstack([self._vectors, vecs])

        # extend metadatas
        for d in docs:
            self._metadatas.append({"id": d.get("id"), "text": d.get("text"), "meta": d.get("meta", {})})

        # (re)build index
        self._build_index()
        # persist raw vectors + metadata
        self._save()

    def _build_index(self):
        if self._vectors is None:
            return
        if _HAS_FAISS:
            xb = self._vectors.astype("float32")
            index = faiss.IndexFlatIP(self.dim)
            faiss.normalize_L2(xb)
            index.add(xb)
            self._faiss_index = index
        else:
            # nothing to precompute for numpy brute-force
            self._faiss_index = None

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        qvec = self.embedder.embed([query]).astype("float32")
        if _HAS_FAISS and self._faiss_index is not None:
            faiss.normalize_L2(qvec)
            D, I = self._faiss_index.search(qvec, k)
            results = []
            for idx in I[0]:
                if idx < 0 or idx >= len(self._metadatas):
                    continue
                results.append(self._metadatas[int(idx)])
            return results

        # numpy brute-force cosine similarity
        if self._vectors is None:
            return []
        xb = self._vectors.astype("float32")
        # ensure normalized
        def norm_rows(a):
            n = np.linalg.norm(a, axis=1, keepdims=True)
            n[n == 0] = 1.0
            return a / n

        xb_n = norm_rows(xb)
        qn = qvec / (np.linalg.norm(qvec) + 1e-9)
        sims = xb_n.dot(qn.reshape(-1))
        idxs = np.argsort(-sims)[:k]
        results = []
        for i in idxs:
            results.append(self._metadatas[int(i)])
        return results

    def _save(self):
        try:
            if self._vectors is None:
                arr = np.zeros((0, self.dim), dtype="float32")
            else:
                arr = self._vectors.astype("float32")
            np.savez(self.index_path, vectors=arr)
            meta_path = self.index_path + ".meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(self._metadatas, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self):
        try:
            npz = np.load(self.index_path + ".npz", allow_pickle=False)
            self._vectors = npz["vectors"]
            meta_path = self.index_path + ".meta.json"
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._metadatas = json.load(f)
            self._build_index()
        except Exception:
            pass
