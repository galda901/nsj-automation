import json
import os
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.database import engine
from recruitment.models.candidate import now_utc
from recruitment.models.job import JobPosition
from recruitment.models.notification import WorkerState
from recruitment.services.email_ingestion import ingest_gmail_daily
from recruitment.services.matching_engine import match_candidates_for_job
from recruitment.services.notifications import (
    NotificationConfigurationError,
    deliver_pending_notifications,
    enqueue_match_notifications,
)


class WorkerLockUnavailable(RuntimeError):
    pass


class WorkerFileLock:
    """Cross-platform process lock for the single local worker instance."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle = None

    def __enter__(self) -> "WorkerFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+b")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.write(b"0")
            self._handle.flush()
        self._handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as error:
            self._handle.close()
            self._handle = None
            raise WorkerLockUnavailable(f"Worker lock is already held: {self.path}") from error
        return self

    def __exit__(self, *_: object) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def run_worker_cycle() -> dict[str, Any]:
    settings = get_settings()
    started_at = now_utc()
    summary: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "job_ids": [],
        "candidate_ids": [],
        "jobs_matched": 0,
        "matches_evaluated": 0,
        "notifications_created": 0,
        "errors": [],
    }
    _update_worker_state("running", started_at=started_at, summary=summary)
    try:
        with Session(engine) as session:
            ingestion = ingest_gmail_daily(session)
            session.commit()
        summary["ingestion"] = ingestion
        job_ids = set(ingestion.get("job_ids", []))
        candidate_ids = set(ingestion.get("candidate_ids", []))
        summary["job_ids"] = sorted(job_ids)
        summary["candidate_ids"] = sorted(candidate_ids)

        with Session(engine) as session:
            active_jobs = list(
                session.exec(select(JobPosition).where(JobPosition.status != "closed")).all()
            )
        if candidate_ids:
            job_ids.update(job.id for job in active_jobs)

        with Session(engine) as session:
            notification_error: str | None = None
            for job_id in sorted(job_ids):
                try:
                    results = match_candidates_for_job(
                        job_id, session, candidate_limit=None
                    )
                except LookupError as error:
                    summary["errors"].append(str(error))
                    continue
                summary["jobs_matched"] += 1
                summary["matches_evaluated"] += len(results)
                if notification_error is None:
                    try:
                        summary["notifications_created"] += enqueue_match_notifications(
                            session, results, settings
                        )
                    except NotificationConfigurationError as error:
                        notification_error = str(error)
                        summary["errors"].append(notification_error)
            session.commit()

        with Session(engine) as session:
            summary["delivery"] = deliver_pending_notifications(session, settings)
        finished_at = now_utc()
        summary["finished_at"] = finished_at.isoformat()
        final_status = "error" if summary["errors"] else "idle"
        _update_worker_state(
            final_status,
            finished_at=finished_at,
            success_at=finished_at if not summary["errors"] else None,
            summary=summary,
            error="; ".join(summary["errors"]) if summary["errors"] else None,
        )
        return summary
    except Exception as error:
        finished_at = now_utc()
        summary["finished_at"] = finished_at.isoformat()
        summary["errors"].append(str(error))
        _update_worker_state(
            "error",
            finished_at=finished_at,
            summary=summary,
            error=str(error),
        )
        return summary


def _update_worker_state(
    status: str,
    *,
    started_at=None,
    finished_at=None,
    success_at=None,
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    settings = get_settings()
    with Session(engine) as session:
        state = session.get(WorkerState, "gmail-matching-worker")
        if state is None:
            state = WorkerState(id="gmail-matching-worker")
        state.status = status
        if started_at is not None:
            state.last_started_at = started_at
        if finished_at is not None:
            state.last_finished_at = finished_at
        if success_at is not None:
            state.last_success_at = success_at
        state.next_run_at = now_utc() + timedelta(seconds=settings.worker_poll_seconds)
        state.last_error = error[:2000] if error else None
        if summary is not None:
            state.last_summary_json = json.dumps(summary, ensure_ascii=False, default=str)
        state.updated_at = now_utc()
        session.add(state)
        session.commit()


def worker_loop(once: bool = False) -> Iterator[dict[str, Any]]:
    settings = get_settings()
    with WorkerFileLock(settings.worker_lock_file):
        while True:
            yield run_worker_cycle()
            if once:
                return
            time.sleep(max(settings.worker_poll_seconds, 5))
