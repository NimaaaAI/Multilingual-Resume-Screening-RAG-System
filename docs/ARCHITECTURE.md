# Architecture

Pipeline, as built so far: **ingestion → embedding → entity graph → hybrid search → graph
expansion → rerank → explain → evaluate**. Finalized further in Phase 8.

## Pipeline

1. **Ingestion** (`api/app/parser.py`, `api/app/chunker.py`) — PDF/DOCX/txt resumes and job
   descriptions are parsed to plain text, language-detected (English/Persian), and split into
   overlapping word-based chunks sized for resume-style text.
2. **Background processing** (`api/app/tasks.py`) — `/upload` saves the file and enqueues a job
   (Redis + RQ) instead of blocking; a worker process picks it up and runs the rest of this
   pipeline.
3. **Embedding** (`api/app/embedder.py`) — each chunk gets a vector embedding
   (`intfloat/multilingual-e5-base`), stored in Postgres via the `pgvector` extension.
4. **Entity graph extraction** (`api/app/entities.py`, `api/app/llm.py`) — an LLM (OpenAI-compatible
   API) extracts skills/companies/titles/institutions from resume text as structured JSON; these
   become `Entity` rows connected to the candidate via `EntityEdge` rows (e.g.
   candidate -[has_skill]-> Python).
5. **Hybrid search** (`api/app/search.py`) — keyword search (Postgres full-text) and vector search
   (pgvector cosine distance) over resume chunks, combined via Reciprocal Rank Fusion.
6. **Graph expansion** (`api/app/search.py::expand_via_graph`) — required skills are extracted from
   the job description and traversed through `EntityEdge` to surface candidates connected via the
   graph even when their resume text doesn't literally match the JD.
7. **Reranking** (`api/app/reranker.py`) — a cross-encoder
   (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) scores the fused, graph-expanded candidate pool
   against the job description for the final ordering.
8. **Explanation** (`api/app/explain.py`) — for each shortlisted candidate, an LLM call generates a
   short explanation grounded in their best-matching resume snippet, in the job description's
   detected language. Served via `GET /results/{job_id}`.

## Evaluation harness

A small golden dataset lives in `eval/golden_dataset/`: one job description (`job.txt`), three
resumes of clearly different relevance (`resumes/strong_match.txt`, `partial_match.txt`,
`poor_match.txt`), and a human-assigned ideal ranking (`ideal_ranking.json`).

`python -m api.app.eval.run` pushes these through the real pipeline (the same
`rank_job_posting` function the `/results` endpoint uses, not a separate code path), then scores
the resulting order against the ideal ranking using **Precision@k** (fraction of the ideal top-k
that appear in the predicted top-k, `k` = size of the ideal ranking).

Wired into CI as a non-blocking step (`eval` job in `.github/workflows/ci.yml`) — it reports the
score in the Actions log without failing the build, so drift is visible over time. It runs only if
an `LLM_API_KEY` GitHub secret is configured (real API calls cost money per run, so this isn't
required by default); if absent, the step logs that it's skipped rather than failing.
