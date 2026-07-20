import uuid

from api.app.db.models import Candidate, Chunk, JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.ingestion.chunker import chunk_text
from api.app.ingestion.parser import detect_language, parse_docx, parse_pdf, parse_txt

PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "txt": parse_txt,
}


def process_resume(file_path: str, file_type: str) -> int:
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    text = PARSERS[file_type](raw_bytes)
    language = detect_language(text)

    session = SessionLocal()
    try:
        # Real candidate identity isn't known yet — Phase 3's entity extraction fills this in.
        # A placeholder row lets the resume/chunks exist without waiting on that step.
        candidate = Candidate(name="Unknown", email=f"pending-{uuid.uuid4()}@placeholder.local")
        session.add(candidate)
        session.flush()  # populate candidate.id without committing yet

        resume = Resume(candidate_id=candidate.id, raw_text=text, file_type=file_type, language=language)
        session.add(resume)
        session.flush()

        for index, chunk in enumerate(chunk_text(text)):
            session.add(Chunk(resume_id=resume.id, text=chunk, chunk_index=index))

        session.commit()
        return resume.id
    finally:
        session.close()


def process_job_posting(file_path: str, file_type: str, title: str) -> int:
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    text = PARSERS[file_type](raw_bytes)
    language = detect_language(text)

    session = SessionLocal()
    try:
        job_posting = JobPosting(title=title, raw_text=text, language=language)
        session.add(job_posting)
        session.flush()

        for index, chunk in enumerate(chunk_text(text)):
            session.add(Chunk(job_posting_id=job_posting.id, text=chunk, chunk_index=index))

        session.commit()
        return job_posting.id
    finally:
        session.close()
