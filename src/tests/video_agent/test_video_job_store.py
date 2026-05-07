from __future__ import annotations

from src.video_agent.services.video_job_store import DemoVideoJobStore


def test_job_store_lifecycle() -> None:
    store = DemoVideoJobStore()
    job = store.create_job(video_path="/tmp/x.mp4")
    assert job.status == "pending"
    fetched = store.get(job.job_id)
    assert fetched is not None
    assert fetched.video_path == "/tmp/x.mp4"

    store.update(job.job_id, status="running")
    assert store.get(job.job_id).status == "running"

    store.update(job.job_id, status="completed", raw_output='{"ok": true}', parsed={"ok": True})
    final = store.get(job.job_id)
    assert final.status == "completed"
    assert final.parsed == {"ok": True}
