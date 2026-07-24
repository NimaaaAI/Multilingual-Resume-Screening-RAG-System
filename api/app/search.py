from sqlalchemy import func

from api.app.db.models import Chunk, Entity, EntityEdge
from api.app.embedder import embed_query


def keyword_search(session, query_text: str, limit: int = 20) -> list[tuple[int, float]]:
    tsvector = func.to_tsvector("english", Chunk.text)
    tsquery = func.plainto_tsquery("english", query_text)
    rank = func.ts_rank(tsvector, tsquery)

    rows = (
        session.query(Chunk.id, rank.label("rank"))
        .filter(Chunk.resume_id.isnot(None))
        .filter(tsvector.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(limit)
        .all()
    )
    return [(row.id, row.rank) for row in rows]


def vector_search(session, query_text: str, limit: int = 20) -> list[tuple[int, float]]:
    query_embedding = embed_query(query_text)
    distance = Chunk.embedding.cosine_distance(query_embedding)

    rows = (
        session.query(Chunk.id, distance.label("distance"))
        .filter(Chunk.resume_id.isnot(None))
        .filter(Chunk.embedding.isnot(None))
        .order_by(distance)
        .limit(limit)
        .all()
    )
    return [(row.id, row.distance) for row in rows]


def reciprocal_rank_fusion(*ranked_lists: list[tuple[int, float]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranked_list in ranked_lists:
        for rank, (chunk_id, _) in enumerate(ranked_list, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def expand_via_graph(session, skill_names: list[str]) -> set[int]:
    """Given required skill names from a JD, find candidate_ids connected via has_skill edges —
    catches candidates whose resume text doesn't literally match but whose graph does."""
    if not skill_names:
        return set()

    lowered = [s.lower() for s in skill_names]
    skill_ids = [
        row.id
        for row in session.query(Entity.id).filter(Entity.type == "skill", func.lower(Entity.name).in_(lowered)).all()
    ]
    if not skill_ids:
        return set()

    candidate_entity_ids = [
        row.entity_id_a
        for row in session.query(EntityEdge.entity_id_a)
        .filter(EntityEdge.entity_id_b.in_(skill_ids), EntityEdge.relation == "has_skill")
        .all()
    ]
    if not candidate_entity_ids:
        return set()

    candidate_ids = [
        row.candidate_id
        for row in session.query(Entity.candidate_id)
        .filter(Entity.id.in_(candidate_entity_ids), Entity.candidate_id.isnot(None))
        .all()
    ]
    return set(candidate_ids)
