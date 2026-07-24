from fastapi import APIRouter

from api.app.db.models import Candidate, Chunk, JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.entities import extract_entities
from api.app.reranker import rerank
from api.app.search import expand_via_graph, keyword_search, reciprocal_rank_fusion, vector_search

router = APIRouter()


@router.get("/rank/{job_posting_id}")
def rank_candidates(job_posting_id: int, limit: int = 10):
    session = SessionLocal()
    try:
        job_posting = session.get(JobPosting, job_posting_id)
        if job_posting is None:
            return {"error": "job posting not found"}

        query_text = job_posting.raw_text

        fused_scores = reciprocal_rank_fusion(
            keyword_search(session, query_text),
            vector_search(session, query_text),
        )

        candidate_scores: dict[int, float] = {}
        if fused_scores:
            chunk_rows = (
                session.query(Chunk.id, Resume.candidate_id)
                .join(Resume, Resume.id == Chunk.resume_id)
                .filter(Chunk.id.in_(fused_scores.keys()))
                .all()
            )
            for chunk_id, candidate_id in chunk_rows:
                candidate_scores[candidate_id] = max(candidate_scores.get(candidate_id, 0.0), fused_scores[chunk_id])

        # Graph expansion: pull in candidates connected to the JD's required skills, even if
        # their resume text didn't literally match the keyword/vector search above.
        try:
            required_skills = extract_entities(query_text).get("skills", [])
        except Exception:
            required_skills = []

        for candidate_id in expand_via_graph(session, required_skills):
            candidate_scores.setdefault(candidate_id, 0.0)

        if not candidate_scores:
            return {"candidates": []}

        candidates = (
            session.query(Candidate.id, Candidate.name, Resume.raw_text)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .filter(Candidate.id.in_(candidate_scores.keys()))
            .all()
        )

        reranked = rerank(query_text, [(row.id, row.raw_text) for row in candidates])

        return {
            "candidates": [
                {"candidate_id": candidate_id, "score": float(score)} for candidate_id, score in reranked[:limit]
            ]
        }
    finally:
        session.close()
