import uuid

from api.app.db.models import Candidate, Chunk, JobPosting, Resume
from api.app.db.session import SessionLocal
from api.app.embeddings.embedder import embed_texts
from api.app.graph.entities import extract_entities, save_entities
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
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks) if chunks else []

    session = SessionLocal()
    try:
        # Real candidate identity isn't known yet — the entity extraction below fills in the
        # graph side, but a placeholder row lets the resume/chunks exist without waiting on it.
        candidate = Candidate(name="Unknown", email=f"pending-{uuid.uuid4()}@placeholder.local")
        session.add(candidate)
        session.flush()  # populate candidate.id without committing yet

        resume = Resume(candidate_id=candidate.id, raw_text=text, file_type=file_type, language=language)
        session.add(resume)
        session.flush()

        first_chunk_id = None
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_row = Chunk(resume_id=resume.id, text=chunk, chunk_index=index, embedding=embedding)
            session.add(chunk_row)
            session.flush()
            if first_chunk_id is None:
                first_chunk_id = chunk_row.id

        extracted = extract_entities(text)
        save_entities(session, candidate_id=candidate.id, extracted=extracted, source_chunk_id=first_chunk_id)

        session.commit()
        return resume.id
    finally:
        session.close()


def process_job_posting(file_path: str, file_type: str, title: str) -> int:
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    text = PARSERS[file_type](raw_bytes)
    language = detect_language(text)
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks) if chunks else []

    session = SessionLocal()
    try:
        job_posting = JobPosting(title=title, raw_text=text, language=language)
        session.add(job_posting)
        session.flush()

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            session.add(Chunk(job_posting_id=job_posting.id, text=chunk, chunk_index=index, embedding=embedding))

        session.commit()
        return job_posting.id
    finally:
        session.close()
