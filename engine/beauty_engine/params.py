from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def clamp(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
      number = float(value)
    except (TypeError, ValueError):
      number = default
    if number < minimum:
      return minimum
    if number > maximum:
      return maximum
    return number


def get_any(payload: dict[str, Any], snake: str, camel: str, default: float) -> float:
    if snake in payload:
        return payload[snake]
    if camel in payload:
        return payload[camel]
    return default


@dataclass(frozen=True)
class LiquifyParams:
    face_slim: float = 0.0
    jawline: float = 0.0
    chin_length: float = 0.0
    eye_enlarge: float = 0.0
    nose_slim: float = 0.0
    smile: float = 0.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "LiquifyParams":
        payload = payload or {}
        return cls(
            face_slim=clamp(get_any(payload, "face_slim", "faceSlim", 0), 0, 1, 0),
            jawline=clamp(get_any(payload, "jawline", "jawline", 0), 0, 1, 0),
            chin_length=clamp(get_any(payload, "chin_length", "chinLength", 0), -1, 1, 0),
            eye_enlarge=clamp(get_any(payload, "eye_enlarge", "eyeEnlarge", 0), 0, 1, 0),
            nose_slim=clamp(get_any(payload, "nose_slim", "noseSlim", 0), 0, 1, 0),
            smile=clamp(get_any(payload, "smile", "smile", 0), 0, 1, 0),
        )


@dataclass(frozen=True)
class SkinParams:
    skin_smooth: float = 0.0
    texture_keep: float = 0.7
    blemish_soften: float = 0.0
    skin_tone_even: float = 0.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "SkinParams":
        payload = payload or {}
        return cls(
            skin_smooth=clamp(get_any(payload, "skin_smooth", "skinSmooth", 0), 0, 1, 0),
            texture_keep=clamp(get_any(payload, "texture_keep", "textureKeep", 0.7), 0, 1, 0.7),
            blemish_soften=clamp(get_any(payload, "blemish_soften", "blemishSoften", 0), 0, 1, 0),
            skin_tone_even=clamp(get_any(payload, "skin_tone_even", "skinToneEven", 0), 0, 1, 0),
        )


@dataclass(frozen=True)
class BeautyParams:
    brightness: float = 0.0
    eye_bright: float = 0.0
    teeth_white: float = 0.0
    soft_contrast: float = 0.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "BeautyParams":
        payload = payload or {}
        return cls(
            brightness=clamp(get_any(payload, "brightness", "brightness", 0), -1, 1, 0),
            eye_bright=clamp(get_any(payload, "eye_bright", "eyeBright", 0), 0, 1, 0),
            teeth_white=clamp(get_any(payload, "teeth_white", "teethWhite", 0), 0, 1, 0),
            soft_contrast=clamp(get_any(payload, "soft_contrast", "softContrast", 0), -1, 1, 0),
        )


@dataclass(frozen=True)
class EditParams:
    liquify: LiquifyParams = field(default_factory=LiquifyParams)
    skin: SkinParams = field(default_factory=SkinParams)
    beauty: BeautyParams = field(default_factory=BeautyParams)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "EditParams":
        payload = payload or {}
        return cls(
            liquify=LiquifyParams.from_payload(payload.get("liquify")),
            skin=SkinParams.from_payload(payload.get("skin")),
            beauty=BeautyParams.from_payload(payload.get("beauty")),
        )

    @classmethod
    def from_cli(
        cls,
        face_slim: float = 0,
        jawline: float = 0,
        chin_length: float = 0,
        eye_enlarge: float = 0,
        nose_slim: float = 0,
        smile: float = 0,
        skin_smooth: float = 0,
        texture_keep: float = 70,
        blemish_soften: float = 0,
        skin_tone_even: float = 0,
        brightness: float = 0,
        eye_bright: float = 0,
        teeth_white: float = 0,
        soft_contrast: float = 0,
    ) -> "EditParams":
        return cls.from_payload(
            {
                "liquify": {
                    "face_slim": face_slim / 100,
                    "jawline": jawline / 100,
                    "chin_length": chin_length / 50,
                    "eye_enlarge": eye_enlarge / 100,
                    "nose_slim": nose_slim / 100,
                    "smile": smile / 100,
                },
                "skin": {
                    "skin_smooth": skin_smooth / 100,
                    "texture_keep": texture_keep / 100,
                    "blemish_soften": blemish_soften / 100,
                    "skin_tone_even": skin_tone_even / 100,
                },
                "beauty": {
                    "brightness": brightness / 50,
                    "eye_bright": eye_bright / 100,
                    "teeth_white": teeth_white / 100,
                    "soft_contrast": soft_contrast / 50,
                },
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
