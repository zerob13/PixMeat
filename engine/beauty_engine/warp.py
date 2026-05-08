from __future__ import annotations

import cv2
import numpy as np


def identity_maps(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    height, width = shape
    x, y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    return x, y


def remap(image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray, interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
    return cv2.remap(
        image.astype(np.float32),
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        interpolation=interpolation,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def masked_blend(base: np.ndarray, overlay: np.ndarray, mask: np.ndarray) -> np.ndarray:
    alpha = np.clip(mask, 0, 1)[..., None].astype(np.float32)
    return np.clip(base * (1.0 - alpha) + overlay * alpha, 0.0, 1.0)


def apply_translation(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    height, width = image.shape[:2]
    map_x, map_y = identity_maps((height, width))
    return remap(image, map_x - dx, map_y - dy)


def mls_similarity_maps(
    shape: tuple[int, int],
    source_handles: np.ndarray,
    target_handles: np.ndarray,
    *,
    max_grid_points: int = 18_000,
    alpha: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    height, width = shape
    source = np.asarray(source_handles, dtype=np.float32).reshape(-1, 2)
    target = np.asarray(target_handles, dtype=np.float32).reshape(-1, 2)
    if source.shape != target.shape:
        raise ValueError("source_handles and target_handles must have the same shape")
    if source.shape[0] == 0 or np.allclose(source, target, atol=1e-4):
        return identity_maps(shape)

    grid_width, grid_height = _dense_grid_size(width, height, max_grid_points)
    grid_x = np.linspace(0, width - 1, grid_width, dtype=np.float32)
    grid_y = np.linspace(0, height - 1, grid_height, dtype=np.float32)
    query_x, query_y = np.meshgrid(grid_x, grid_y)
    queries = np.column_stack([query_x.reshape(-1), query_y.reshape(-1)]).astype(np.float32)

    mapped = _mls_similarity_points(queries, target, source, alpha=alpha)
    sparse_x = mapped[:, 0].reshape(grid_height, grid_width).astype(np.float32)
    sparse_y = mapped[:, 1].reshape(grid_height, grid_width).astype(np.float32)

    map_x = cv2.resize(sparse_x, (width, height), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(sparse_y, (width, height), interpolation=cv2.INTER_CUBIC)
    return _clamp_maps(map_x, map_y, width, height)


def jacobian_determinant(map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    dx_x = np.gradient(map_x.astype(np.float32), axis=1)
    dy_x = np.gradient(map_x.astype(np.float32), axis=0)
    dx_y = np.gradient(map_y.astype(np.float32), axis=1)
    dy_y = np.gradient(map_y.astype(np.float32), axis=0)
    return (dx_x * dy_y - dy_x * dx_y).astype(np.float32)


def _mls_similarity_points(
    queries: np.ndarray,
    source_handles: np.ndarray,
    target_handles: np.ndarray,
    *,
    alpha: float,
    chunk_size: int = 4096,
) -> np.ndarray:
    result = np.empty_like(queries, dtype=np.float32)
    source = source_handles.astype(np.float32)
    target = target_handles.astype(np.float32)
    eps = np.float32(1e-6)

    for start in range(0, queries.shape[0], chunk_size):
        end = min(start + chunk_size, queries.shape[0])
        query = queries[start:end].astype(np.float32)
        diff = query[:, None, :] - source[None, :, :]
        dist2 = np.sum(diff * diff, axis=2)
        exact = dist2 < 1e-7
        weights = 1.0 / np.maximum(dist2, eps) ** alpha
        weight_sum = np.sum(weights, axis=1, keepdims=True)

        source_star = (weights[:, :, None] * source[None, :, :]).sum(axis=1) / weight_sum
        target_star = (weights[:, :, None] * target[None, :, :]).sum(axis=1) / weight_sum
        source_hat = source[None, :, :] - source_star[:, None, :]
        target_hat = target[None, :, :] - target_star[:, None, :]

        mu = np.sum(weights * np.sum(source_hat * source_hat, axis=2), axis=1)
        mu = np.maximum(mu, eps)
        a = np.sum(
            weights * (source_hat[:, :, 0] * target_hat[:, :, 0] + source_hat[:, :, 1] * target_hat[:, :, 1]),
            axis=1,
        ) / mu
        b = np.sum(
            weights * (source_hat[:, :, 0] * target_hat[:, :, 1] - source_hat[:, :, 1] * target_hat[:, :, 0]),
            axis=1,
        ) / mu

        delta = query - source_star
        mapped = np.empty_like(query, dtype=np.float32)
        mapped[:, 0] = target_star[:, 0] + a * delta[:, 0] - b * delta[:, 1]
        mapped[:, 1] = target_star[:, 1] + b * delta[:, 0] + a * delta[:, 1]

        if np.any(exact):
            rows = np.where(exact.any(axis=1))[0]
            cols = np.argmax(exact[rows], axis=1)
            mapped[rows] = target[cols]
        result[start:end] = mapped
    return result


def _dense_grid_size(width: int, height: int, max_grid_points: int) -> tuple[int, int]:
    aspect = width / max(height, 1)
    grid_height = int(round(np.sqrt(max_grid_points / max(aspect, 1e-3))))
    grid_width = int(round(grid_height * aspect))
    grid_width = int(np.clip(grid_width, 32, min(width, 192)))
    grid_height = int(np.clip(grid_height, 32, min(height, 192)))
    return grid_width, grid_height


def _clamp_maps(
    map_x: np.ndarray,
    map_y: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.clip(map_x.astype(np.float32), 0, max(0, width - 1)),
        np.clip(map_y.astype(np.float32), 0, max(0, height - 1)),
    )
