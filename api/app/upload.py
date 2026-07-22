import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from redis import Redis
from rq import Queue

from api.app.config import settings
from api.app.tasks import process_job_posting, process_resume

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

queue = Queue(connection=Redis.from_url(settings.redis_url))


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    file_type = file.filename.rsplit(".", 1)[-1].lower()
    dest = UPLOADS_DIR / f"{uuid.uuid4()}.{file_type}"
    dest.write_bytes(await file.read())
    return str(dest), file_type


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(default=[]),
    job_description: UploadFile | None = File(default=None),
    job_title: str = Form(default=""),
):
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
