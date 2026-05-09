from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .analysis import AnalysisV2
from .api import run_stdio
from .debug import draw_landmarks
from .diagnostics import get_health
from .face import detect_faces
from .io import read_image, to_uint8, write_image
from .masks import build_masks
from .models.model_config import AnalysisConfig
from .params import EditParams
from .pipeline import process_image
from .session import legacy_faces_from_analysis


def main() -> None:
    parser = argparse.ArgumentParser(prog="beauty-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("serve")

    process = subparsers.add_parser("process")
    process.add_argument("input")
    process.add_argument("output")
    add_param_args(process)
    add_analysis_args(process)
    process.add_argument("--debug-dir")

    debug = subparsers.add_parser("debug-masks")
    debug.add_argument("input")
    debug.add_argument("debug_dir")

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("input")
    analyze.add_argument("debug_dir")
    add_analysis_args(analyze)

    args = parser.parse_args()
    if args.command == "health":
        print(json.dumps(get_health(), indent=2))
    elif args.command == "serve":
        run_stdio()
    elif args.command == "process":
        run_process(args)
    elif args.command == "debug-masks":
        run_debug_masks(args.input, args.debug_dir)
    elif args.command == "analyze":
        run_analyze(args)


def add_param_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--body-slim", type=float, default=0)
    parser.add_argument("--waist-slim", type=float, default=0)
    parser.add_argument("--arm-slim", type=float, default=0)
    parser.add_argument("--face-slim", type=float, default=0)
    parser.add_argument("--jawline", type=float, default=0)
    parser.add_argument("--chin-length", type=float, default=0)
    parser.add_argument("--eye-enlarge", type=float, default=0)
    parser.add_argument("--nose-slim", type=float, default=0)
    parser.add_argument("--smile", type=float, default=0)
    parser.add_argument("--skin-smooth", type=float, default=0)
    parser.add_argument("--texture-keep", type=float, default=70)
    parser.add_argument("--blemish-soften", type=float, default=0)
    parser.add_argument("--skin-tone-even", type=float, default=0)
    parser.add_argument("--brightness", type=float, default=0)
    parser.add_argument("--eye-bright", type=float, default=0)
    parser.add_argument("--teeth-white", type=float, default=0)
    parser.add_argument("--soft-contrast", type=float, default=0)


def add_analysis_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--analysis-version", choices=["v1", "v2"], default=None)
    parser.add_argument("--analysis-device", choices=["auto", "cpu", "cuda", "mps"], default=None)
    parser.add_argument("--face-detector-model")
    parser.add_argument("--face-landmarker-model")
    parser.add_argument("--person-segmentation-model")
    parser.add_argument("--human-parsing-model")


def params_from_args(args: argparse.Namespace) -> EditParams:
    return EditParams.from_cli(
        body_slim=args.body_slim,
        waist_slim=args.waist_slim,
        arm_slim=args.arm_slim,
        face_slim=args.face_slim,
        jawline=args.jawline,
        chin_length=args.chin_length,
        eye_enlarge=args.eye_enlarge,
        nose_slim=args.nose_slim,
        smile=args.smile,
        skin_smooth=args.skin_smooth,
        texture_keep=args.texture_keep,
        blemish_soften=args.blemish_soften,
        skin_tone_even=args.skin_tone_even,
        brightness=args.brightness,
        eye_bright=args.eye_bright,
        teeth_white=args.teeth_white,
        soft_contrast=args.soft_contrast,
    )


def run_process(args: argparse.Namespace) -> None:
    image = read_image(args.input)
    analysis_result = run_analysis_if_enabled(args, image.rgb, args.debug_dir)
    faces = legacy_faces_from_analysis(analysis_result) if analysis_result is not None else detect_faces(image.rgb)
    debug_dir = Path(args.debug_dir) if args.debug_dir else None
    if debug_dir and faces:
        debug_dir.mkdir(parents=True, exist_ok=True)
        draw_landmarks(image.rgb, faces[0], debug_dir / "landmarks.png")
    result = process_image(
        image.rgb,
        faces,
        faces[0].face_id if faces else None,
        params_from_args(args),
        analysis_result=analysis_result,
        debug_dir=debug_dir,
    )
    write_image(args.output, result, alpha=image.alpha, exif=image.exif)
    print(json.dumps({"ok": True, "output": str(Path(args.output)), "faces": len(faces)}))


def run_analyze(args: argparse.Namespace) -> None:
    image = read_image(args.input)
    config = analysis_config_from_args(args, debug_dir=args.debug_dir, default_version="v2")
    bgr = cv2.cvtColor(to_uint8(image.rgb), cv2.COLOR_RGB2BGR)
    result = AnalysisV2(config).analyze(bgr)
    print(json.dumps({"ok": True, "debug_dir": str(Path(args.debug_dir)), "analysis": result.to_json()}, indent=2))


def run_analysis_if_enabled(args: argparse.Namespace, rgb, debug_dir: str | None):
    config = analysis_config_from_args(args, debug_dir=debug_dir, default_version="v1")
    if config.version != "v2":
        return None
    bgr = cv2.cvtColor(to_uint8(rgb), cv2.COLOR_RGB2BGR)
    return AnalysisV2(config).analyze(bgr)


def analysis_config_from_args(
    args: argparse.Namespace,
    *,
    debug_dir: str | None,
    default_version: str,
) -> AnalysisConfig:
    base = AnalysisConfig.from_env()
    model_paths = {
        "face_detector": getattr(args, "face_detector_model", None),
        "face_landmarker": getattr(args, "face_landmarker_model", None),
        "person_segmentation": getattr(args, "person_segmentation_model", None),
        "human_parsing": getattr(args, "human_parsing_model", None),
    }
    explicit_version = getattr(args, "analysis_version", None)
    payload = {
        "version": explicit_version or (default_version if default_version == "v2" else base.version),
        "debug": bool(debug_dir) or base.debug,
        "debug_dir": debug_dir or base.debug_dir,
        "device": getattr(args, "analysis_device", None) or base.device,
        "model_paths": {key: value for key, value in model_paths.items() if value},
    }
    return AnalysisConfig.from_payload(payload, base=base)


def run_debug_masks(input_path: str, debug_dir: str) -> None:
    image = read_image(input_path)
    faces = detect_faces(image.rgb)
    if not faces:
        print(json.dumps({"ok": False, "error": "no_face"}))
        return
    output = Path(debug_dir)
    output.mkdir(parents=True, exist_ok=True)
    masks = build_masks(image.rgb.shape[:2], faces[0])
    from .debug import write_mask

    paths = {
        "landmarks": output / "landmarks.png",
        "face_mask": output / "face_mask.png",
        "skin_mask": output / "skin_mask.png",
        "refined_skin_mask": output / "refined_skin_mask.png",
        "eye_mask": output / "eye_mask.png",
        "mouth_mask": output / "mouth_mask.png",
    }
    draw_landmarks(image.rgb, faces[0], paths["landmarks"])
    write_mask(paths["face_mask"], masks.face)
    write_mask(paths["skin_mask"], masks.skin)
    from .smoothing import refined_skin_mask

    write_mask(paths["refined_skin_mask"], refined_skin_mask(image.rgb, masks))
    write_mask(paths["eye_mask"], masks.eyes)
    write_mask(paths["mouth_mask"], masks.mouth)
    print(json.dumps({"ok": True, "paths": {key: str(value) for key, value in paths.items()}}, indent=2))


if __name__ == "__main__":
    main()
