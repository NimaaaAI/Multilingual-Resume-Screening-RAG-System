from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app.main import app
from api.app.workers.tasks import process_job_posting, process_resume

client = TestClient(app)


def test_upload_enqueues_job_without_blocking():
    with patch("api.app.routes.upload.queue") as mock_queue:
        mock_queue.enqueue.return_value = MagicMock(id="fake-job-id")

        response = client.post(
            "/upload",
            files={"files": ("resume.txt", b"Experienced software engineer.", "text/plain")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data == {"jobs": [{"filename": "resume.txt", "job_id": "fake-job-id"}]}

    mock_queue.enqueue.assert_called_once()
    args, _ = mock_queue.enqueue.call_args
    assert args[0] is process_resume
    assert args[2] == "txt"


def test_upload_enqueues_job_description():
    with patch("api.app.routes.upload.queue") as mock_queue:
        mock_queue.enqueue.return_value = MagicMock(id="fake-job-id")

        response = client.post(
            "/upload",
            data={"job_title": "Backend Engineer"},
            files={"job_description": ("jd.txt", b"Looking for a backend engineer.", "text/plain")},
        )

    assert response.status_code == 200
    args, _ = mock_queue.enqueue.call_args
    assert args[0] is process_job_posting
    assert args[2] == "txt"
    assert args[3] == "Backend Engineer"
