"""Kernel Density Estimation (KDE) module for particle cloud spatial probability density.

Evaluates 2D continuous probability densities over particle ensembles in local metric (X, Y) coordinates.
"""

from typing import Optional, Sequence, Tuple, Union
import numpy as np

try:
    from scipy.stats import gaussian_kde
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def estimate_kde(
    x: Union[Sequence[float], np.ndarray],
    y: Union[Sequence[float], np.ndarray],
    grid_resolution: int = 100,
    padding_factor: float = 0.1,
    bandwidth_method: Optional[Union[str, float]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Estimate 2D continuous spatial probability density for particle X, Y coordinates in meters.

    Args:
        x: 1D sequence/array of particle X coordinates in meters.
        y: 1D sequence/array of particle Y coordinates in meters.
        grid_resolution: Number of grid points along each axis for 2D evaluation (default: 100).
        padding_factor: Fractional margin added around the particle cloud bounding box (default: 0.1).
        bandwidth_method: Optional bandwidth estimation method passed to scipy gaussian_kde ('scott', 'silverman', or scalar).

    Returns:
        Tuple of (grid_x, grid_y, density):
            - grid_x: 2D numpy array of evaluation X coordinates in meters (shape: grid_resolution x grid_resolution).
            - grid_y: 2D numpy array of evaluation Y coordinates in meters (shape: grid_resolution x grid_resolution).
            - density: 2D numpy array of estimated probability density values (shape: grid_resolution x grid_resolution).

    Raises:
        ImportError: If scipy package is not installed.
        ValueError: If x and y have mismatched lengths or insufficient valid data points.
    """
    if not SCIPY_AVAILABLE:
        raise ImportError(
            "scipy package is not installed. Please install scipy to perform Kernel Density Estimation."
        )

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if x_arr.ndim != 1 or y_arr.ndim != 1:
        x_arr = x_arr.ravel()
        y_arr = y_arr.ravel()

    if len(x_arr) != len(y_arr):
        raise ValueError(
            f"X and Y coordinate arrays must have the same length (got len(x)={len(x_arr)}, len(y)={len(y_arr)})."
        )

    if len(x_arr) < 2:
        raise ValueError(
            f"At least 2 particle coordinates are required for KDE estimation (got {len(x_arr)})."
        )

    valid_mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_valid = x_arr[valid_mask]
    y_valid = y_arr[valid_mask]

    if len(x_valid) < 2:
        raise ValueError(
            f"At least 2 valid (non-NaN, non-Inf) particle coordinates are required for KDE estimation (got {len(x_valid)})."
        )

    values = np.vstack([x_valid, y_valid])
    kde = gaussian_kde(values, bw_method=bandwidth_method)

    x_min, x_max = float(np.min(x_valid)), float(np.max(x_valid))
    y_min, y_max = float(np.min(y_valid)), float(np.max(y_valid))

    x_span = x_max - x_min
    y_span = y_max - y_min

    margin_x = x_span * padding_factor if x_span > 0 else 100.0
    margin_y = y_span * padding_factor if y_span > 0 else 100.0

    grid_x, grid_y = np.meshgrid(
        np.linspace(x_min - margin_x, x_max + margin_x, grid_resolution),
        np.linspace(y_min - margin_y, y_max + margin_y, grid_resolution),
    )

    grid_coords = np.vstack([grid_x.ravel(), grid_y.ravel()])
    density = kde(grid_coords).reshape(grid_x.shape)

    return grid_x, grid_y, density
