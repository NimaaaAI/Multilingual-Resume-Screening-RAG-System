import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from redis import Redis
from rq import Queue

from api.app.config import settings
from api.app.tasks import process_job_posting, process_resume

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_FILE_TYPES = {"pdf", "docx", "txt"}

queue = Queue(connection=Redis.from_url(settings.redis_url))


def _file_type(filename: str) -> str:
    if "." not in filename:
        raise HTTPException(status_code=400, detail=f"'{filename}' has no file extension")
    file_type = filename.rsplit(".", 1)[-1].lower()
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '.{file_type}' for '{filename}'")
    return file_type


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    file_type = _file_type(file.filename)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail=f"'{file.filename}' is empty")

    dest = UPLOADS_DIR / f"{uuid.uuid4()}.{file_type}"
    dest.write_bytes(raw_bytes)
    return str(dest), file_type


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(default=[]),
    job_description: UploadFile | None = File(default=None),
    job_title: str = Form(default=""),
):
    if not files and job_description is None:
        raise HTTPException(status_code=400, detail="Provide at least one resume file or a job description")

    jobs = []

    for file in files:
        dest, file_type = await _save_upload(file)
        job = queue.enqueue(process_resume, dest, file_type)
        jobs.append({"filename": file.filename, "job_id": job.id})

    if job_description is not None:
        dest, file_type = await _save_upload(job_description)
        job = queue.enqueue(process_job_posting, dest, file_type, job_title)
        jobs.append({"filename": job_description.filename, "job_id": job.id})

    return {"jobs": jobs}
