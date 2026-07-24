from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("intfloat/multilingual-e5-base")


def embed_texts(texts: list[str]) -> list[list[float]]:
    # multilingual-e5 models are trained with a "passage: " prefix for indexed text (vs "query: "
    # for search queries at retrieval time in Phase 4) — improves retrieval quality noticeably.
    prefixed = [f"passage: {t}" for t in texts]
    return _model.encode(prefixed, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return _model.encode(f"query: {text}", normalize_embeddings=True).tolist()
