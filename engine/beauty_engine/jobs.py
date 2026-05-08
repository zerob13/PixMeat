from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class JobState:
    job_id: str
    cancel_requested: bool = False


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = Lock()

    def start(self, job_id: str) -> JobState:
        with self._lock:
            state = JobState(job_id)
            self._jobs[job_id] = state
            return state

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                state = JobState(job_id, cancel_requested=True)
                self._jobs[job_id] = state
            else:
                state.cancel_requested = True
            return state.cancel_requested

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return bool(self._jobs.get(job_id) and self._jobs[job_id].cancel_requested)

    def finish(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
