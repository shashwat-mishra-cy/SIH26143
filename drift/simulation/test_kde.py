"""Test suite for Kernel Density Estimation (KDE) module (kde.py).

Validates 2D spatial density estimation over particle ensembles and handles invalid input errors.
"""

from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.kde import estimate_kde, SCIPY_AVAILABLE


def test_kde() -> None:
    assert SCIPY_AVAILABLE, "scipy package is not installed."

    # ---------------------------------------------------------
    # A & B: Synthetic 2D particle cloud around X=0, Y=0 (500 points)
    # ---------------------------------------------------------
    np.random.seed(42)
    x_cloud = np.random.normal(loc=0.0, scale=100.0, size=500)
    y_cloud = np.random.normal(loc=0.0, scale=100.0, size=500)

    # ---------------------------------------------------------
    # C: Run estimate_kde()
    # ---------------------------------------------------------
    grid_resolution = 100
    grid_x, grid_y, density = estimate_kde(x_cloud, y_cloud, grid_resolution=grid_resolution)

    # ---------------------------------------------------------
    # D: Assertions and verification
    # ---------------------------------------------------------
    assert grid_x.ndim == 2, f"Expected 2D grid_x, got ndim={grid_x.ndim}"
    assert grid_y.ndim == 2, f"Expected 2D grid_y, got ndim={grid_y.ndim}"
    assert density.ndim == 2, f"Expected 2D density array, got ndim={density.ndim}"

    expected_shape = (grid_resolution, grid_resolution)
    assert grid_x.shape == expected_shape, f"grid_x shape mismatch: {grid_x.shape} != {expected_shape}"
    assert grid_y.shape == expected_shape, f"grid_y shape mismatch: {grid_y.shape} != {expected_shape}"
    assert density.shape == expected_shape, f"density shape mismatch: {density.shape} != {expected_shape}"

    assert np.all(np.isfinite(density)), "Density array contains NaN or Inf values!"
    assert np.all(density >= 0), "Density array contains negative values!"

    max_density = float(np.max(density))
    assert max_density > 0, f"Maximum density must be greater than zero, got {max_density}"

    # ---------------------------------------------------------
    # F: Test invalid input (mismatched lengths)
    # ---------------------------------------------------------
    x_invalid = np.random.normal(0, 100, 500)
    y_invalid = np.random.normal(0, 100, 400)  # mismatched length

    value_error_raised = False
    try:
        estimate_kde(x_invalid, y_invalid)
    except ValueError as e:
        value_error_raised = True
        assert "same length" in str(e).lower(), f"Unexpected ValueError message: {e}"

    assert value_error_raised, "estimate_kde failed to raise ValueError for mismatched array lengths!"

    # ---------------------------------------------------------
    # E: Output required test summary
    # ---------------------------------------------------------
    print("KDE test: PASSED")
    print(f"Grid shape: {density.shape}")
    print(f"Maximum density: {max_density:.6e}")


if __name__ == "__main__":
    test_kde()
