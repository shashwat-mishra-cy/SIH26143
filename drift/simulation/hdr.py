"""Highest Density Region (HDR) extraction module for 2D Kernel Density Estimation grids.

Extracts smallest spatial regions containing a specified fraction of modelled probability mass (e.g., 50% HDR, 90% HDR)
from local metric X/Y density distributions.
"""

from typing import Any, Dict, Tuple, Union
import numpy as np


def extract_hdr(
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    density: np.ndarray,
    probability_mass: float,
) -> Dict[str, Any]:
    """Extract Highest Density Region (HDR) mask and metrics from a 2D KDE probability density grid.

    An HDR is a highest-density region containing a requested fraction of the MODELLED probability mass.
    It represents the minimal spatial area containing that proportion of the estimated continuous probability density.

    Args:
        grid_x: 2D numpy array of evaluation X coordinates in meters.
        grid_y: 2D numpy array of evaluation Y coordinates in meters.
        density: 2D numpy array of estimated probability density values (m⁻²).
        probability_mass: Target cumulative probability mass fraction (0 < probability_mass <= 1.0).

    Returns:
        Dict[str, Any] containing:
            - 'mask': 2D boolean numpy array indicating grid cells within the HDR.
            - 'threshold': Minimum density value (m⁻²) bounding the HDR.
            - 'requested_mass': Target probability mass fraction requested.
            - 'achieved_mass': Actual cumulative probability mass enclosed by the HDR mask.
            - 'normalized_prob': 2D numpy array of normalized cell probabilities.
            - 'cell_area': Area of each grid cell in square meters (m²).

    Raises:
        ValueError: If input arrays are incompatible, contain invalid values (NaN, Inf, negative),
                    or probability_mass is out of range (0, 1].
    """
    if not (0.0 < probability_mass <= 1.0):
        raise ValueError(
            f"probability_mass must be strictly between 0.0 and 1.0 (got {probability_mass})."
        )

    grid_x_arr = np.asarray(grid_x, dtype=float)
    grid_y_arr = np.asarray(grid_y, dtype=float)
    density_arr = np.asarray(density, dtype=float)

    if grid_x_arr.ndim != 2 or grid_y_arr.ndim != 2 or density_arr.ndim != 2:
        raise ValueError(
            f"grid_x, grid_y, and density must all be 2D arrays (got ndims: {grid_x_arr.ndim}, {grid_y_arr.ndim}, {density_arr.ndim})."
        )

    if not (grid_x_arr.shape == grid_y_arr.shape == density_arr.shape):
        raise ValueError(
            f"Array shape mismatch: grid_x={grid_x_arr.shape}, grid_y={grid_y_arr.shape}, density={density_arr.shape}."
        )

    if grid_x_arr.shape[0] < 2 or grid_x_arr.shape[1] < 2:
        raise ValueError(
            f"Grid shape must be at least 2x2 (got shape {grid_x_arr.shape})."
        )

    if not np.all(np.isfinite(density_arr)):
        raise ValueError("density array contains non-finite values (NaN or Inf).")

    if np.any(density_arr < 0):
        raise ValueError("density array contains negative density values.")

    # Calculate grid cell dimensions and area in square meters (m²)
    # Assumes uniform grid spacing along X and Y axes
    dx = abs(float(grid_x_arr[0, 1] - grid_x_arr[0, 0]))
    dy = abs(float(grid_y_arr[1, 0] - grid_y_arr[0, 0]))
    cell_area = dx * dy

    if cell_area <= 0:
        raise ValueError(f"Calculated grid cell area must be positive (got cell_area={cell_area}).")

    raw_cell_prob = density_arr * cell_area
    total_mass = float(np.sum(raw_cell_prob))

    if total_mass <= 0:
        raise ValueError(f"Total probability mass over grid must be positive (got total_mass={total_mass}).")

    normalized_prob = raw_cell_prob / total_mass

    flat_density = density_arr.ravel()
    flat_norm_prob = normalized_prob.ravel()

    # Sort grid cells by density in descending order
    sorted_indices = np.argsort(flat_density)[::-1]
    sorted_probs = flat_norm_prob[sorted_indices]
    sorted_densities = flat_density[sorted_indices]

    cum_probs = np.cumsum(sorted_probs)
    cutoff_idx = np.searchsorted(cum_probs, probability_mass)

    if cutoff_idx >= len(sorted_indices):
        cutoff_idx = len(sorted_indices) - 1

    density_threshold = float(sorted_densities[cutoff_idx])
    mask = density_arr >= density_threshold
    achieved_mass = float(np.sum(normalized_prob[mask]))

    return {
        "mask": mask,
        "threshold": density_threshold,
        "requested_mass": float(probability_mass),
        "achieved_mass": achieved_mass,
        "normalized_prob": normalized_prob,
        "cell_area": cell_area,
    }
