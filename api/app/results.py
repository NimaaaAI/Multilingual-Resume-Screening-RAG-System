from fastapi import APIRouter, HTTPException

from api.app.config import settings
from api.app.db.models import Candidate, Chunk, JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.entities import extract_entities
from api.app.explain import generate_explanation
from api.app.reranker import rerank
from api.app.search import expand_via_graph, keyword_search, reciprocal_rank_fusion, vector_search

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

        query_text = job_posting.raw_text

        fused_scores = reciprocal_rank_fusion(
            keyword_search(session, query_text),
            vector_search(session, query_text),
        )

        candidate_scores: dict[int, float] = {}
        candidate_best_chunk: dict[int, str] = {}
        if fused_scores:
            chunk_rows = (
                session.query(Chunk.id, Chunk.text, Resume.candidate_id)
                .join(Resume, Resume.id == Chunk.resume_id)
                .filter(Chunk.id.in_(fused_scores.keys()))
                .all()
            )
            for chunk_id, chunk_text, candidate_id in chunk_rows:
                score = fused_scores[chunk_id]
                if score > candidate_scores.get(candidate_id, -1):
                    candidate_scores[candidate_id] = score
                    candidate_best_chunk[candidate_id] = chunk_text

        # Graph expansion: pull in candidates connected to the JD's required skills, even if
        # their resume text didn't literally match the keyword/vector search above.
        try:
            required_skills = extract_entities(query_text).get("skills", [])
        except Exception:
            required_skills = []

        for candidate_id in expand_via_graph(session, required_skills):
            candidate_scores.setdefault(candidate_id, 0.0)

        if not candidate_scores:
            return {"job_title": job_posting.title, "candidates": []}

        candidates = (
            session.query(Candidate.id, Candidate.name, Resume.raw_text)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .filter(Candidate.id.in_(candidate_scores.keys()))
            .all()
        )
        text_by_id = {row.id: row.raw_text for row in candidates}
        name_by_id = {row.id: row.name for row in candidates}

        reranked = rerank(query_text, [(row.id, row.raw_text) for row in candidates])[:limit]

        results = []
        for candidate_id, score in reranked:
            snippet = candidate_best_chunk.get(candidate_id) or text_by_id[candidate_id][:300]
            explanation = generate_explanation(
                job_text=query_text,
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
