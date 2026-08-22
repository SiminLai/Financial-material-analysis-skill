"""
Wrapper scaffold for local BGE-M3 embeddings.

This module provides `BGEEmbeddingProvider` as a placeholder. It expects a
local model directory at `models/bge-m3`. To use a real local model, replace
the `embed` method to call your inference engine (vLLM, transformers+accelerate,
or a local server). Downloading large models must be done manually due to
credentials and environment constraints.
"""
import os
import numpy as np
from typing import List


class BGEEmbeddingProvider:
    def __init__(self, model_path: str = "models/bge-m3", dim: int = 1024):
        self.model_path = model_path
        self.dim = dim
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"BGE model not found at {self.model_path}. Please download and unpack it.")

    def embed(self, texts: List[str]):
        # Placeholder: in real usage, call local inference server or tokenizer+model
        # For now return deterministic pseudo-vectors scaled to requested dim
        out = []
        for t in texts:
            b = t.encode("utf-8", errors="ignore")
            arr = np.frombuffer(b, dtype=np.uint8)
            if len(arr) == 0:
                vec = np.zeros((self.dim,), dtype="float32")
            else:
                vec = np.zeros((self.dim,), dtype="float32")
                for i, val in enumerate(arr):
                    vec[i % self.dim] += float(val)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            out.append(vec)
        return np.vstack(out)
