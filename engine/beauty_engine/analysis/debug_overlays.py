from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from beauty_engine.io import write_image
from beauty_engine.types import AnalysisResult, FaceResult, RegionResult

REGION_COLORS = {
    "face": (255, 196, 64),
    "hair": (60, 60, 80),
    "neck": (255, 160, 120),
    "torso": (90, 160, 255),
    "upper_clothes": (70, 130, 220),
    "lower_clothes": (80, 80, 190),
    "left_arm": (255, 120, 80),
    "right_arm": (255, 90, 120),
    "left_leg": (120, 220, 120),
    "right_leg": (90, 200, 150),
}


def export_debug_overlays(image_bgr: np.ndarray, result: AnalysisResult, debug_dir: str | Path) -> None:
    """Write Analysis V2 debug overlays and compact JSON metadata."""

    output = Path(debug_dir)
    output.mkdir(parents=True, exist_ok=True)
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    write_image(output / "01_faces.png", draw_faces(rgb, result.faces))
    write_image(output / "02_face_landmarks.png", draw_face_landmarks(rgb, result.faces))
    write_mask_rgb(output / "03_person_mask.png", result.masks.get("person_mask"))
    write_image(output / "04_human_parsing_labels.png", draw_label_overlay(rgb, {k: v for k, v in result.masks.items() if k.startswith("parsing_")}))
    write_mask_rgb(output / "05_skin_semantic_mask.png", result.masks.get("skin_semantic_mask"))
    write_mask_rgb(output / "06_skin_color_refine_mask.png", result.masks.get("skin_color_refine_mask"))
    write_mask_rgb(output / "07_skin_final_mask.png", result.masks.get("skin_final_mask"))
    write_image(output / "08_body_regions.png", draw_regions(rgb, result.regions))
    write_image(output / "09_confidence_map.png", confidence_map(rgb.shape[:2], result))
    (output / "analysis_v2.json").write_text(json.dumps(result.to_json(), indent=2), encoding="utf8")


def draw_faces(rgb: np.ndarray, faces: list[FaceResult]) -> np.ndarray:
    canvas = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8).copy()
    for face in faces:
        x, y, w, h = [int(round(value)) for value in face.bbox]
        ex, ey, ew, eh = [int(round(value)) for value in face.expanded_bbox]
        cv2.rectangle(canvas, (ex, ey), (ex + ew, ey + eh), (70, 130, 255), 1)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 180, 0), 2)
        label = f"{face.face_id} {face.score:.2f} {face.source}"
        cv2.putText(canvas, label, (x, max(14, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 230, 80), 1, cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def draw_face_landmarks(rgb: np.ndarray, faces: list[FaceResult]) -> np.ndarray:
    canvas = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8).copy()
    for face in faces:
        if face.landmarks is None:
            continue
        for px, py in face.landmarks[:, :2]:
            x = int(round(float(px)))
            y = int(round(float(py)))
            if 0 <= x < canvas.shape[1] and 0 <= y < canvas.shape[0]:
                cv2.circle(canvas, (x, y), 1, (0, 220, 255), -1)
    return canvas.astype(np.float32) / 255.0


def draw_label_overlay(rgb: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    canvas = np.clip(rgb * 0.38, 0, 1)
    overlay = np.zeros_like(canvas, dtype=np.float32)
    for key, mask in masks.items():
        label = key.removeprefix("parsing_")
        color = np.asarray(REGION_COLORS.get(label, (180, 180, 180)), dtype=np.float32) / 255.0
        alpha = np.clip(mask, 0, 1)[..., None] * 0.72
        overlay = overlay * (1.0 - alpha) + color.reshape(1, 1, 3) * alpha
    return np.clip(canvas + overlay, 0, 1)


def draw_regions(rgb: np.ndarray, regions: dict[str, RegionResult]) -> np.ndarray:
    canvas = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8).copy()
    names = [
        "torso_region",
        "waist_region",
        "left_arm_region",
        "right_arm_region",
        "left_leg_region",
        "right_leg_region",
        "face_region",
    ]
    for index, name in enumerate(names):
        region = regions.get(name)
        if region is None or region.mask.max(initial=0) <= 0:
            continue
        color = _indexed_color(index)
        mask = (region.mask > 0.12).astype(np.uint8)
        contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, color, 2)
        x, y, w, h = [int(round(value)) for value in region.bbox]
        cv2.putText(canvas, name, (x, max(14, y + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def confidence_map(shape: tuple[int, int], result: AnalysisResult) -> np.ndarray:
    height, width = shape
    canvas = np.zeros((height, width, 3), dtype=np.float32)
    values = [
        result.confidence.face_detection,
        result.confidence.face_landmarks,
        result.confidence.person_segmentation,
        result.confidence.human_parsing,
        result.confidence.skin_mask,
    ]
    bar_h = max(8, height // 28)
    for index, value in enumerate(values):
        y = index * (bar_h + 4) + 10
        cv2.rectangle(canvas, (10, y), (10 + int((width - 20) * value), y + bar_h), (value, 1.0 - value * 0.35, 0.18), -1)
    return canvas


def write_mask_rgb(path: Path, mask: np.ndarray | None) -> None:
    if mask is None:
        return
    write_image(path, np.dstack([mask, mask, mask]).astype(np.float32))


def _indexed_color(index: int) -> tuple[int, int, int]:
    colors = [(255, 180, 0), (0, 210, 255), (255, 95, 80), (120, 220, 120), (180, 120, 255), (255, 120, 210)]
    return colors[index % len(colors)]
