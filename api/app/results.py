from fastapi import APIRouter, HTTPException

from api.app.config import settings
from api.app.db.models import Candidate, Chunk, JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.explain import generate_explanation
from api.app.search import keyword_search, rank_job_posting, reciprocal_rank_fusion, vector_search

router = APIRouter()


@router.get("/results/{job_id}")
def get_results(job_id: int, limit: int = 10):
    if not settings.llm_api_key:
        raise HTTPException(status_code=400, detail="LLM_API_KEY is not configured")

    session = SessionLocal()
    try:
        job_posting = session.get(JobPosting, job_id)
        if job_posting is None:
            raise HTTPException(status_code=404, detail=f"Job posting {job_id} not found")

        ranked = rank_job_posting(session, job_posting)[:limit]
        if not ranked:
            return {"job_title": job_posting.title, "candidates": []}

        candidate_ids = [candidate_id for candidate_id, _ in ranked]
        candidates = (
            session.query(Candidate.id, Candidate.name, Resume.raw_text)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .filter(Candidate.id.in_(candidate_ids))
            .all()
        )
        name_by_id = {row.id: row.name for row in candidates}
        text_by_id = {row.id: row.raw_text for row in candidates}

        # Best matching chunk per candidate, used as the grounded citation snippet
        fused_scores = reciprocal_rank_fusion(
            keyword_search(session, job_posting.raw_text),
            vector_search(session, job_posting.raw_text),
        )
        best_chunk: dict[int, str] = {}
        best_score: dict[int, float] = {}
        if fused_scores:
            chunk_rows = (
                session.query(Chunk.id, Chunk.text, Resume.candidate_id)
                .join(Resume, Resume.id == Chunk.resume_id)
                .filter(Chunk.id.in_(fused_scores.keys()))
                .all()
            )
            for chunk_id, chunk_text, candidate_id in chunk_rows:
                score = fused_scores[chunk_id]
                if score > best_score.get(candidate_id, -1):
                    best_score[candidate_id] = score
                    best_chunk[candidate_id] = chunk_text

        results = []
        for candidate_id, score in ranked:
            snippet = best_chunk.get(candidate_id) or text_by_id[candidate_id][:300]
            explanation = generate_explanation(
                job_text=job_posting.raw_text,
                candidate_name=name_by_id[candidate_id],
                snippet=snippet,
                language=job_posting.language,
            )
            results.append(
                {
                    "candidate_id": candidate_id,
                    "name": name_by_id[candidate_id],
                    "score": float(score),
                    "explanation": explanation,
                    "source_snippet": snippet,
                }
            )

        return {"job_title": job_posting.title, "candidates": results}
    finally:
        session.close()
