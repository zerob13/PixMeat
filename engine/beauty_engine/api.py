from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .debug import draw_landmarks
from .diagnostics import get_health
from .errors import EngineError
from .io import read_image, write_image
from .jobs import JobRegistry
from .masks import build_masks
from .params import EditParams
from .pipeline import process_image
from .protocol import error_response, event_message, success_response
from .session import SessionRegistry

Emit = Callable[[dict[str, Any]], None]


class EngineApi:
    def __init__(self, emit: Emit | None = None) -> None:
        self.sessions = SessionRegistry()
        self.jobs = JobRegistry()
        self.preferred_backend = "auto"
        self.emit = emit or (lambda _message: None)

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        try:
            if method == "health":
                return success_response(request_id, get_health(self.preferred_backend))
            if method == "set_backend":
                return success_response(request_id, self.set_backend(params))
            if method == "load_image":
                return success_response(request_id, self.load_image(params))
            if method == "get_session":
                return success_response(request_id, self.get_session(params))
            if method == "render_preview":
                return success_response(request_id, self.render_preview(params))
            if method == "export_image":
                return success_response(request_id, self.export_image(params))
            if method == "cancel_job":
                return success_response(request_id, self.cancel_job(params))
            if method == "debug_render_masks":
                return success_response(request_id, self.debug_render_masks(params))
            raise EngineError("unknown_method", f"Unknown method: {method}")
        except EngineError as exc:
            return error_response(request_id, exc.code, exc.message, exc.details)
        except Exception as exc:
            return error_response(request_id, "processing_error", str(exc))

    def set_backend(self, params: dict[str, Any]) -> dict[str, Any]:
        backend = str(params.get("backend", "auto"))
        if backend not in {"auto", "cpu", "cuda", "mps", "opencv_cuda"}:
            raise EngineError("backend_unavailable", f"Unsupported backend: {backend}")
        self.preferred_backend = backend
        health = get_health(backend)
        self.emit(event_message("backend_changed", {"active_backend": health["active_backend"]}))
        return {"active_backend": health["active_backend"], "fallback_backend": "cpu"}

    def load_image(self, params: dict[str, Any]) -> dict[str, Any]:
        image_path = params.get("image_path")
        if not image_path:
            raise EngineError("read_error", "image_path is required")
        session = self.sessions.load_image(
            str(image_path),
            preview_max_side=int(params.get("preview_max_side", 1600)),
            detect=bool(params.get("detect_faces", True)),
        )
        return session.to_json()

    def get_session(self, params: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(params)
        return session.to_json()

    def render_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        session = self._get_session(params)
        image = read_image(session.preview_path)
        edit_params = EditParams.from_payload(params.get("params"))
        faces = session.faces_for_size(session.preview_width, session.preview_height)
        token = str(params.get("request_token", f"preview_{int(time.time() * 1000)}"))
        result = process_image(
            image.rgb,
            faces,
            params.get("active_face_id") or session.active_face_id,
            edit_params,
        )
        output_path = session.cache_dir / f"preview_{safe_name(token)}.png"
        write_image(output_path, result)
        elapsed = int((time.perf_counter() - started) * 1000)
        return {
            "request_token": token,
            "image_id": session.image_id,
            "preview_result_path": str(output_path),
            "width": session.preview_width,
            "height": session.preview_height,
            "backend": get_health(self.preferred_backend)["active_backend"],
            "elapsed_ms": elapsed,
        }

    def export_image(self, params: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        session = self._get_session(params)
        output_path = Path(str(params.get("output_path", "")))
        if not output_path:
            raise EngineError("write_error", "output_path is required")
        job_id = str(params.get("job_id") or f"job_{int(time.time() * 1000)}")
        self.jobs.start(job_id)

        def progress(value: float, stage: str) -> None:
            if self.jobs.is_cancelled(job_id):
                raise EngineError("job_cancelled", f"Job cancelled: {job_id}")
            self.emit(event_message("job_progress", {"job_id": job_id, "progress": value, "stage": stage}))

        try:
            progress(0.02, "loading_original")
            original = read_image(session.source_path)
            edit_params = EditParams.from_payload(params.get("params"))
            faces = session.faces_for_size(original.width, original.height)
            result = process_image(
                original.rgb,
                faces,
                params.get("active_face_id") or session.active_face_id,
                edit_params,
                progress=progress,
            )
            temp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
            progress(0.96, "writing")
            write_image(
                temp_path,
                result,
                alpha=original.alpha,
                quality=int(params.get("quality", 92)),
                keep_metadata=bool(params.get("keep_metadata", True)),
                exif=original.exif,
            )
            shutil.move(str(temp_path), str(output_path))
            elapsed = int((time.perf_counter() - started) * 1000)
            self.emit(event_message("job_completed", {"job_id": job_id, "output_path": str(output_path)}))
            return {
                "job_id": job_id,
                "output_path": str(output_path),
                "backend": get_health(self.preferred_backend)["active_backend"],
                "elapsed_ms": elapsed,
            }
        finally:
            self.jobs.finish(job_id)

    def cancel_job(self, params: dict[str, Any]) -> dict[str, Any]:
        job_id = str(params.get("job_id", ""))
        if not job_id:
            raise EngineError("job_cancelled", "job_id is required")
        cancel_requested = self.jobs.cancel(job_id)
        self.emit(event_message("job_cancelled", {"job_id": job_id}))
        return {"job_id": job_id, "cancel_requested": cancel_requested}

    def debug_render_masks(self, params: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(params)
        faces = session.faces_for_size(session.preview_width, session.preview_height)
        face = next((item for item in faces if item.face_id == params.get("face_id")), faces[0] if faces else None)
        if face is None:
            raise EngineError("no_face", "No face available for debug masks")
        image = read_image(session.preview_path)
        masks = build_masks(image.rgb.shape[:2], face)
        debug_dir = session.cache_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        from .debug import write_mask

        refined_path = debug_dir / "refined_skin_mask.png"
        from .smoothing import refined_skin_mask

        paths = {
            "landmarks": debug_dir / "landmarks.png",
            "face_mask": debug_dir / "face_mask.png",
            "skin_mask": debug_dir / "skin_mask.png",
            "refined_skin_mask": refined_path,
        }
        draw_landmarks(image.rgb, face, paths["landmarks"])
        write_mask(paths["face_mask"], masks.face)
        write_mask(paths["skin_mask"], masks.skin)
        write_mask(refined_path, refined_skin_mask(image.rgb, masks))
        return {"paths": {key: str(value) for key, value in paths.items()}}

    def _get_session(self, params: dict[str, Any]):
        image_id = str(params.get("image_id", ""))
        session = self.sessions.get(image_id)
        if session is None:
            raise EngineError("image_not_found", f"Unknown image_id: {image_id}")
        return session


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)


def run_stdio() -> None:
    def emit(message: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    api = EngineApi(emit=emit)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = api.handle(request)
        except json.JSONDecodeError as exc:
            response = error_response(None, "invalid_json", "Invalid JSON request", {"cause": str(exc)})
        emit(response)


if __name__ == "__main__":
    run_stdio()
