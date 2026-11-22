"""
score.py - ELA Heuristic Scoring Engine for ForensiScan
Computes a rule-based statistical suspicion score (0.0 to 1.0) based on error level distributions.
IMPORTANT: This is purely a deterministic heuristic metric derived from compression discrepancies.
It is NOT a machine learning or CNN classification verdict.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def calculate_ela_score(
    raw_diff: np.ndarray,
    amplified_ela: Optional[np.ndarray] = None,
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Compute the ELA Heuristic Score (0.00 to 1.00) and descriptive metrics.

    Args:
        raw_diff: 3D uint8 array (H, W, 3) of unscaled absolute differences.
        amplified_ela: Optional 3D uint8 array of auto-scaled ELA image.
        bounding_boxes: Optional list of detected bounding boxes from heatmap analysis.

    Returns:
        tuple containing:
            - suspicion_score (float): Clamped score from 0.00 to 1.00.
            - heuristic_label (str): "Low suspicion" | "Medium suspicion" | "High suspicion".
            - score_details (dict): Granular statistical breakdown and diagnostic factors.
    """
    if raw_diff.ndim == 3:
        gray_diff = cv2.cvtColor(raw_diff, cv2.COLOR_RGB2GRAY).astype(np.float32)
    else:
        gray_diff = raw_diff.astype(np.float32)

    h, w = gray_diff.shape[:2]
    total_pixels = max(1, h * w)

    # 1. Distribution summary
    mean_intensity = float(np.mean(gray_diff))
    max_intensity = float(np.max(gray_diff))
    std_intensity = float(np.std(gray_diff))

    # 2. High error pixel ratio (unscaled pixel error >= 8)
    high_threshold = 8.0
    high_pixel_count = int(np.sum(gray_diff >= high_threshold))
    high_pixel_ratio = float(high_pixel_count / total_pixels)

    # 3. Spatial concentration (16x16 grid analysis)
    grid_rows, grid_cols = 16, 16
    block_h = max(4, h // grid_rows)
    block_w = max(4, w // grid_cols)

    block_means: List[float] = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            y1, y2 = r * block_h, min(h, (r + 1) * block_h)
            x1, x2 = c * block_w, min(w, (c + 1) * block_w)
            if y2 > y1 and x2 > x1:
                block_means.append(float(np.mean(gray_diff[y1:y2, x1:x2])))

    b_arr = np.array(block_means) if block_means else np.array([0.0])
    median_block = float(np.median(b_arr))
    p95_block = float(np.percentile(b_arr, 95))

    # Contrast ratio between 95th percentile hot block and median block
    contrast_ratio = (p95_block + 1e-4) / (median_block + 0.06)
    concentration_factor = min(1.0, max(0.0, (contrast_ratio - 2.5) / 5.0))

    # Peak-to-background ratio
    peak_ratio = max_intensity / (mean_intensity + 0.5)
    peak_factor = min(1.0, max(0.0, (peak_ratio - 8.0) / 18.0))

    # High error share factor
    high_share_factor = min(1.0, high_pixel_ratio / 0.04)

    # Standard deviation factor
    std_factor = min(1.0, std_intensity / 3.0)

    # Detected ROI count factor: 1 to 2 discrete isolated anomalies is typical of splicing
    roi_count = len(bounding_boxes) if bounding_boxes else 0
    if 1 <= roi_count <= 2:
        roi_factor = 0.85
    elif roi_count > 2:
        roi_factor = 0.25  # Multiple scattered ROIs typically indicate texture/edge artifacts
    else:
        roi_factor = 0.0

    # Weighted heuristic combination:
    # - Spatial concentration: 35%
    # - Peak-to-background ratio: 25%
    # - High error pixel share: 15%
    # - Variance / standard deviation: 15%
    # - Isolated ROI factor: 10%
    raw_score = (
        0.35 * concentration_factor +
        0.25 * peak_factor +
        0.15 * high_share_factor +
        0.15 * std_factor +
        0.10 * roi_factor
    )

    suspicion_score = float(np.clip(round(raw_score, 2), 0.02, 0.98))

    # Assign descriptive heuristic suspicion label
    # Note: Explicitly avoid "Authentic/Tampered" - label purely as suspicion level
    if suspicion_score < 0.35:
        heuristic_label = "Low suspicion"
    elif suspicion_score < 0.65:
        heuristic_label = "Medium suspicion"
    else:
        heuristic_label = "High suspicion"

    score_details = {
        "metric_type": "ELA heuristic score (rule-based statistical analysis)",
        "mean_intensity": round(mean_intensity, 2),
        "max_intensity": int(max_intensity),
        "std_intensity": round(std_intensity, 2),
        "high_pixel_ratio_pct": round(high_pixel_ratio * 100, 2),
        "spatial_concentration_ratio": round(contrast_ratio, 2),
        "peak_to_mean_ratio": round(peak_ratio, 2),
        "detected_roi_count": roi_count,
        "is_machine_learning": False,
        "model_architecture": "Deterministic heuristic (CNN in training)"
    }

    logger.debug(
        f"Computed ELA heuristic score: {suspicion_score:.2f} ({heuristic_label}) | "
        f"Mean={mean_intensity:.2f}, HighRatio={high_pixel_ratio*100:.1f}%, Concentration={contrast_ratio:.2f}"
    )

    return suspicion_score, heuristic_label, score_details
