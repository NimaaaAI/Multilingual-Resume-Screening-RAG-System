import json
from pathlib import Path

from api.app.db.models import JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.search import rank_job_posting
from api.app.tasks import process_job_posting, process_resume

GOLDEN_DIR = Path(__file__).resolve().parents[3] / "eval" / "golden_dataset"


def precision_at_k(predicted_filenames: list[str], ideal_filenames: list[str], k: int) -> float:
    ideal_top_k = set(ideal_filenames[:k])
    if not ideal_top_k:
        return 0.0
    predicted_top_k = set(predicted_filenames[:k])
    return len(predicted_top_k & ideal_top_k) / len(ideal_top_k)


def run() -> float:
    job_text = (GOLDEN_DIR / "job.txt").read_text()
    ideal_ranking = json.loads((GOLDEN_DIR / "ideal_ranking.json").read_text())
    resume_paths = sorted((GOLDEN_DIR / "resumes").glob("*.txt"))

    # Write the JD to a temp file so we can reuse the real ingestion function unchanged.
    jd_path = GOLDEN_DIR / "_job_tmp.txt"
    jd_path.write_text(job_text)
    job_posting_id = process_job_posting(str(jd_path), "txt", "Golden Eval Job")
    jd_path.unlink()

    candidate_id_to_filename = {}
    for resume_path in resume_paths:
        resume_id = process_resume(str(resume_path), "txt")
        session = SessionLocal()
        try:
            resume = session.get(Resume, resume_id)
            candidate_id_to_filename[resume.candidate_id] = resume_path.name
        finally:
            session.close()

    session = SessionLocal()
    try:
        job_posting = session.get(JobPosting, job_posting_id)
        ranked = rank_job_posting(session, job_posting)
    finally:
        session.close()

    # The dev database has candidates from earlier manual testing too — restrict to this run's
    # golden-dataset candidates only, so unrelated leftover data doesn't affect the score.
    predicted_filenames = [
        candidate_id_to_filename[candidate_id] for candidate_id, _ in ranked if candidate_id in candidate_id_to_filename
    ]

    score = precision_at_k(predicted_filenames, ideal_ranking, k=len(ideal_ranking))
    print(f"Predicted ranking: {predicted_filenames}")
    print(f"Ideal ranking:     {ideal_ranking}")
    print(f"Precision@{len(ideal_ranking)}: {score:.2f}")
    return score


if __name__ == "__main__":
    run()
