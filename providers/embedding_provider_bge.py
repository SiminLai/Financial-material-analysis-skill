import numpy as np
from typing import List

try:
    from FlagEmbedding import FlagModel
    _HAS_FLAG = True
    print(">>> FlagEmbedding import SUCCESS")
except Exception as e:
    FlagModel = None
    _HAS_FLAG = False
    print(">>> FlagEmbedding import FAILED:", e)


class BGEEmbeddingProvider:

    def __init__(
        self,
        model_path: str = None,
        locale: str = "en",
        use_fp16: bool = True,
        batch_size: int = 16,
        max_length: int = 512,
    ):

        print(">>> BGEEmbeddingProvider INIT START")
        print(">>> HAS_FLAG:", _HAS_FLAG)

        if model_path is None:
            if locale and str(locale).lower().startswith('zh'):
                model_path = "BAAI/bge-small-zh-v1.5"
            else:
                model_path = "BAAI/bge-small-en-v1.5"

        print(">>> Loading BGE model:", model_path)

        self.model_path = model_path
        self.batch_size = batch_size
        self.max_length = max_length


        if _HAS_FLAG and FlagModel is not None:

            print(">>> Creating FlagModel...")

            self.model = FlagModel(
                model_path,
                use_fp16=use_fp16,
            )

            print(">>> BGE MODEL LOADED SUCCESS")

            self.dim = self._get_embedding_dim()

            print(">>> BGE EMBEDDING DIM:", self.dim)

        else:
            print(">>> Using fallback embedding")

            from providers.embedding_provider import EmbeddingProvider as StubEmbed
            self._stub = StubEmbed(dim=128)
            self.dim = getattr(self._stub, 'dim', 128)


    def _get_embedding_dim(self) -> int:

        print(">>> Testing dummy embedding dimension")

        test_embedding = self.model.encode(
            ["dimension_test"],
            batch_size=1,
            max_length=self.max_length,
        )

        print(
            ">>> Dummy embedding shape:",
            test_embedding.shape
        )

        return test_embedding.shape[-1]

    @staticmethod
    def _normalize(
        vectors: np.ndarray
    ) -> np.ndarray:

        vectors = vectors / (
            np.linalg.norm(
                vectors,
                axis=1,
                keepdims=True
            ) + 1e-12
        )

        return vectors.astype("float32")


    def embed_documents(
        self,
        texts: List[str]
    ) -> np.ndarray:

        """
        Document embedding
        Used for:
        - PDF chunks
        - vector database indexing
        """

        if _HAS_FLAG and getattr(self, "model", None) is not None:

            vectors = self.model.encode_corpus(
                texts,
                batch_size=self.batch_size,
                max_length=self.max_length,
            )

            return self._normalize(vectors)


        return self._normalize(
            self._stub.embed(texts)
        )


    def embed_query(
        self,
        queries: List[str]
    ) -> np.ndarray:

        """
        Query embedding
        Used for:
        - similarity search
        """

        if _HAS_FLAG and getattr(self, "model", None) is not None:

            vectors = self.model.encode_queries(
                queries,
                batch_size=self.batch_size,
                max_length=self.max_length,
            )

            return self._normalize(vectors)


        return self._normalize(
            self._stub.embed(queries)
        )


    def embed(
        self,
        texts: List[str]
    ) -> np.ndarray:

        # backward compatibility
        return self.embed_documents(texts)
