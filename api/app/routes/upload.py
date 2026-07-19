import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile
from redis import Redis
from rq import Queue

from api.app.config import settings
from api.app.workers.tasks import process_resume

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

queue = Queue(connection=Redis.from_url(settings.redis_url))


@router.post("/upload")
async def upload_resumes(files: list[UploadFile]):
    jobs = []
    for file in files:
        file_type = file.filename.rsplit(".", 1)[-1].lower()
        dest = UPLOADS_DIR / f"{uuid.uuid4()}.{file_type}"
        dest.write_bytes(await file.read())

        job = queue.enqueue(process_resume, str(dest), file_type)
        jobs.append({"filename": file.filename, "job_id": job.id})

    return {"jobs": jobs}
