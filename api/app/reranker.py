from sentence_transformers import CrossEncoder

# Multilingual cross-encoder trained on mMARCO. Persian coverage isn't explicitly confirmed in
# its training data, so reranking quality for Persian resumes may be weaker than English — matches
# the "note the Persian limitation" caveat from the original spec.
_model = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")


def rerank(query: str, candidates: list[tuple[int, str]]) -> list[tuple[int, float]]:
    """candidates: (candidate_id, resume_text) pairs. Returns (candidate_id, score) sorted desc."""
    if not candidates:
        return []

    pairs = [(query, text) for _, text in candidates]
    scores = _model.predict(pairs)
    scored = list(zip((c[0] for c in candidates), scores))
    return sorted(scored, key=lambda x: x[1], reverse=True)
