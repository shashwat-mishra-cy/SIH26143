"""Test suite for Highest Density Region (HDR) extraction module (hdr.py).

Validates 50% and 90% HDR extraction, mask shapes, cell counts, density thresholds, and input validation error handling.
"""

from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.kde import estimate_kde, SCIPY_AVAILABLE
from drift.simulation.hdr import extract_hdr


def test_hdr() -> None:
    assert SCIPY_AVAILABLE, "scipy package is not installed."

    # ---------------------------------------------------------
    # 1. Generate synthetic 2D particle cloud (500 particles)
    # ---------------------------------------------------------
    np.random.seed(42)
    x_cloud = np.random.normal(loc=0.0, scale=100.0, size=500)
    y_cloud = np.random.normal(loc=0.0, scale=100.0, size=500)

    grid_x, grid_y, density = estimate_kde(x_cloud, y_cloud, grid_resolution=100)

    # ---------------------------------------------------------
    # 2. Extract 50% HDR and 90% HDR
    # ---------------------------------------------------------
    hdr_50 = extract_hdr(grid_x, grid_y, density, probability_mass=0.50)
    hdr_90 = extract_hdr(grid_x, grid_y, density, probability_mass=0.90)

    # ---------------------------------------------------------
    # 3. Assertions and verifications
    # ---------------------------------------------------------
    assert hdr_50["mask"].shape == density.shape, f"Mask shape mismatch: {hdr_50['mask'].shape} != {density.shape}"
    assert hdr_90["mask"].shape == density.shape, f"Mask shape mismatch: {hdr_90['mask'].shape} != {density.shape}"

    assert hdr_50["mask"].dtype == bool, f"Expected boolean mask, got {hdr_50['mask'].dtype}"
    assert hdr_90["mask"].dtype == bool, f"Expected boolean mask, got {hdr_90['mask'].dtype}"

    assert np.isfinite(hdr_50["threshold"]), f"Non-finite threshold for 50% HDR: {hdr_50['threshold']}"
    assert np.isfinite(hdr_90["threshold"]), f"Non-finite threshold for 90% HDR: {hdr_90['threshold']}"

    assert abs(hdr_50["achieved_mass"] - 0.50) < 0.05, f"Achieved 50% mass out of tolerance: {hdr_50['achieved_mass']}"
    assert abs(hdr_90["achieved_mass"] - 0.90) < 0.05, f"Achieved 90% mass out of tolerance: {hdr_90['achieved_mass']}"

    count_50 = int(np.sum(hdr_50["mask"]))
    count_90 = int(np.sum(hdr_90["mask"]))
    assert count_50 <= count_90, f"50% HDR should contain fewer/equal cells than 90% HDR ({count_50} > {count_90})"

    # ---------------------------------------------------------
    # 4. Test invalid probability values raise ValueError
    # ---------------------------------------------------------
    for invalid_prob in [0.0, -0.5, 1.5]:
        val_error = False
        try:
            extract_hdr(grid_x, grid_y, density, probability_mass=invalid_prob)
        except ValueError:
            val_error = True
        assert val_error, f"Failed to raise ValueError for invalid probability_mass={invalid_prob}"

    # ---------------------------------------------------------
    # 5. Test mismatched grid/density shapes raise ValueError
    # ---------------------------------------------------------
    bad_density = density[:-1, :]  # Mismatched shape
    mismatch_error = False
    try:
        extract_hdr(grid_x, grid_y, bad_density, probability_mass=0.50)
    except ValueError:
        mismatch_error = True
    assert mismatch_error, "Failed to raise ValueError for mismatched grid/density shapes"

    # ---------------------------------------------------------
    # 6. Test invalid density values (NaN, Inf, negative) raise ValueError
    # ---------------------------------------------------------
    nan_density = density.copy()
    nan_density[10, 10] = np.nan
    nan_error = False
    try:
        extract_hdr(grid_x, grid_y, nan_density, probability_mass=0.50)
    except ValueError:
        nan_error = True
    assert nan_error, "Failed to raise ValueError for NaN density values"

    neg_density = density.copy()
    neg_density[10, 10] = -1.0
    neg_error = False
    try:
        extract_hdr(grid_x, grid_y, neg_density, probability_mass=0.50)
    except ValueError:
        neg_error = True
    assert neg_error, "Failed to raise ValueError for negative density values"

    # ---------------------------------------------------------
    # Summary Output
    # ---------------------------------------------------------
    print("HDR extraction tests: PASSED")
    print(f"- 50% HDR achieved probability: {hdr_50['achieved_mass']:.6f}")
    print(f"- 50% HDR selected cells: {count_50}")
    print(f"- 50% HDR density threshold: {hdr_50['threshold']:.6e} m⁻²")
    print(f"- 90% HDR achieved probability: {hdr_90['achieved_mass']:.6f}")
    print(f"- 90% HDR selected cells: {count_90}")
    print(f"- 90% HDR density threshold: {hdr_90['threshold']:.6e} m⁻²")
    print(f"- Grid cell area: {hdr_50['cell_area']:.2f} m² (assumes uniform dx * dy spacing)")


if __name__ == "__main__":
    test_hdr()
