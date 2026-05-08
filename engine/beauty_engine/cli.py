from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import run_stdio
from .debug import draw_landmarks
from .diagnostics import get_health
from .face import detect_faces
from .io import read_image, write_image
from .masks import build_masks
from .params import EditParams
from .pipeline import process_image


def main() -> None:
    parser = argparse.ArgumentParser(prog="beauty-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("serve")

    process = subparsers.add_parser("process")
    process.add_argument("input")
    process.add_argument("output")
    add_param_args(process)
    process.add_argument("--debug-dir")

    debug = subparsers.add_parser("debug-masks")
    debug.add_argument("input")
    debug.add_argument("debug_dir")

    args = parser.parse_args()
    if args.command == "health":
        print(json.dumps(get_health(), indent=2))
    elif args.command == "serve":
        run_stdio()
    elif args.command == "process":
        run_process(args)
    elif args.command == "debug-masks":
        run_debug_masks(args.input, args.debug_dir)


def add_param_args(parser: argparse.ArgumentParser) -> None:
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


def params_from_args(args: argparse.Namespace) -> EditParams:
    return EditParams.from_cli(
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
    faces = detect_faces(image.rgb)
    debug_dir = Path(args.debug_dir) if args.debug_dir else None
    if debug_dir and faces:
        debug_dir.mkdir(parents=True, exist_ok=True)
        draw_landmarks(image.rgb, faces[0], debug_dir / "landmarks.png")
    result = process_image(image.rgb, faces, faces[0].face_id if faces else None, params_from_args(args), debug_dir=debug_dir)
    write_image(args.output, result, alpha=image.alpha, exif=image.exif)
    print(json.dumps({"ok": True, "output": str(Path(args.output)), "faces": len(faces)}))


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
        "eye_mask": output / "eye_mask.png",
        "mouth_mask": output / "mouth_mask.png",
    }
    draw_landmarks(image.rgb, faces[0], paths["landmarks"])
    write_mask(paths["face_mask"], masks.face)
    write_mask(paths["skin_mask"], masks.skin)
    write_mask(paths["eye_mask"], masks.eyes)
    write_mask(paths["mouth_mask"], masks.mouth)
    print(json.dumps({"ok": True, "paths": {key: str(value) for key, value in paths.items()}}, indent=2))


if __name__ == "__main__":
    main()
