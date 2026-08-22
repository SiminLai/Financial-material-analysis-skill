import hashlib
import numpy as np
from typing import List


class EmbeddingProvider:
    """Offline deterministic pseudo-embedding generator.

    Produces a fixed-size float32 vector for a given text using an MD5 digest
    expanded into a vector. This is meant as a replaceable stub for real
    embedding APIs; it is deterministic and requires no external deps.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, texts: List[str]):
        out = []
        for t in texts:
            # create md5 digest and expand into required dimension
            h = hashlib.md5(t.encode("utf-8")).digest()
            # repeat digest as needed
            reps = (self.dim + len(h) - 1) // len(h)
            big = (h * reps)[: self.dim]
            vec = np.frombuffer(big, dtype=np.uint8).astype("float32")
            # normalize to unit vector
            norm = np.linalg.norm(vec)
            if norm == 0:
                out.append(vec)
            else:
                out.append(vec / norm)
        return np.vstack(out)
