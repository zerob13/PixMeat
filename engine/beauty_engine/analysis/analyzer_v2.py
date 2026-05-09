from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from beauty_engine.models.model_config import AnalysisConfig
from beauty_engine.types import AnalysisResult, FaceResult

from .confidence import aggregate_confidence, score_face_bbox
from .debug_overlays import export_debug_overlays
from .face_detector import FaceDetectorV2
from .face_landmarks import FaceLandmarkRunner
from .human_parsing import HumanParserV2
from .model_registry import ModelRegistry
from .person_segmentation import PersonSegmenterV2
from .region_builder import build_regions
from .skin_mask import build_skin_masks_v2


class AnalysisV2:
    """Production-oriented image analysis pipeline for local retouching.

    The pipeline accepts OpenCV-style BGR uint8 images and returns all geometry
    in original image coordinates. Optional models are loaded only from local
    configured paths; missing weights produce a degraded but usable result.
    """

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config.normalized()
        self.registry = ModelRegistry(self.config)
        self.face_landmarks = FaceLandmarkRunner(self.registry)
        self.face_detector = FaceDetectorV2(self.registry)
        self.person_segmenter = PersonSegmenterV2(self.registry)
        self.human_parser = HumanParserV2(self.registry)

    def analyze(self, image_bgr: np.ndarray) -> AnalysisResult:
        """Analyze one BGR uint8 image and optionally export debug overlays."""

        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("AnalysisV2 expects a BGR image shaped HxWx3")
        if image_bgr.dtype != np.uint8:
            raise ValueError("AnalysisV2 expects a uint8 image")

        started_total = time.perf_counter()
        height, width = image_bgr.shape[:2]
        timings: dict[str, int] = {}

        started = time.perf_counter()
        faces = self.face_landmarks.detect_full_image(image_bgr)
        face_source = "face_landmarker"
        if not faces:
            faces = self.face_detector.detect(image_bgr)
            face_source = "classic_face_detector"
        faces = self.face_landmarks.landmark_faces(image_bgr, faces)
        faces = _sort_and_rekey_faces(faces, (width, height))
        selected_face_id = faces[0].face_id if faces else None
        timings["faces_ms"] = _elapsed_ms(started)

        started = time.perf_counter()
        person_mask, persons, person_confidence, person_source = self.person_segmenter.segment(image_bgr, faces)
        selected_person_id = persons[0].person_id if persons else None
        timings["person_segmentation_ms"] = _elapsed_ms(started)

        started = time.perf_counter()
        parsing_masks, parsing_confidence, parsing_source = self.human_parser.parse(image_bgr, person_mask, faces, persons)
        timings["human_parsing_ms"] = _elapsed_ms(started)

        started = time.perf_counter()
        skin_masks, skin_confidence = build_skin_masks_v2(image_bgr, person_mask, parsing_masks, faces)
        timings["skin_mask_ms"] = _elapsed_ms(started)

        started = time.perf_counter()
        regions = build_regions((height, width), faces, persons, parsing_masks, person_mask, parsing_source=parsing_source)
        timings["regions_ms"] = _elapsed_ms(started)

        face_detection_confidence = float(faces[0].confidence) if faces else 0.0
        face_landmark_confidence = (
            float(faces[0].quality.landmark_confidence)
            if faces and faces[0].quality is not None and faces[0].landmarks is not None
            else 0.0
        )
        confidence = aggregate_confidence(
            face_detection=face_detection_confidence,
            face_landmarks=face_landmark_confidence,
            person_segmentation=person_confidence,
            human_parsing=parsing_confidence,
            skin_mask=skin_confidence,
        )

        masks: dict[str, np.ndarray] = {"person_mask": person_mask.astype(np.float32)}
        masks.update({f"parsing_{name}": mask.astype(np.float32) for name, mask in parsing_masks.items()})
        masks.update({name: mask.astype(np.float32) for name, mask in skin_masks.items()})

        timings["total_ms"] = _elapsed_ms(started_total)
        debug: dict[str, Any] = {
            "analysis_version": "v2",
            "device": self.config.device,
            "image_size": [width, height],
            "inference_scale": 1.0,
            "scale_factors": {"x": 1.0, "y": 1.0},
            "sources": {
                "faces": face_source,
                "person_segmentation": person_source,
                "human_parsing": parsing_source,
                "skin_mask": "semantic+color_refinement+exclusions",
            },
            "timings_ms": timings,
            "debug_dir": self.config.debug_dir,
        }

        result = AnalysisResult(
            image_size=(width, height),
            faces=faces,
            selected_face_id=selected_face_id,
            persons=persons,
            selected_person_id=selected_person_id,
            masks=masks,
            regions=regions,
            confidence=confidence,
            debug=debug,
            model_backends=dict(self.registry.backend_info),
        )

        if self.config.debug:
            debug_dir = self.config.debug_dir or str(Path.cwd() / "analysis_v2_debug")
            export_debug_overlays(image_bgr, result, debug_dir)
        return result


def _sort_and_rekey_faces(faces: list[FaceResult], image_size: tuple[int, int]) -> list[FaceResult]:
    width, height = image_size
    sorted_faces = sorted(
        faces,
        key=lambda face: score_face_bbox(face.bbox, (width, height), face.confidence),
        reverse=True,
    )
    output: list[FaceResult] = []
    for index, face in enumerate(sorted_faces, start=1):
        output.append(
            replace(
                face,
                face_id=f"face_{index}",
                score=score_face_bbox(face.bbox, (width, height), face.confidence),
            )
        )
    return output


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
