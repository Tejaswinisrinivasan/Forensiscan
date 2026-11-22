"""
heatmap.py - ELA Heatmap and Suspicious Region Detector for ForensiScan
Smooths ELA intensity, applies INFERNO/JET colormaps, alpha-blends over the original image,
and extracts bounding boxes around high-discrepancy regions.
"""

import logging
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def generate_heatmap_and_boxes(
    original_image: Image.Image,
    ela_image: Image.Image,
    colormap_type: str = "INFERNO",
    alpha: float = 0.52
) -> Tuple[Image.Image, Image.Image, np.ndarray, List[Dict[str, int]]]:
    """
    Generate an ELA heatmap overlay and detect suspicious bounding box regions.

    Args:
        original_image: PIL Image of the original input (RGB).
        ela_image: PIL Image of the amplified ELA output (RGB).
        colormap_type: "INFERNO" or "JET" (default: "INFERNO").
        alpha: Alpha blending weight for the colormap overlay (0.0 to 1.0).

    Returns:
        tuple containing:
            - heatmap_overlay (PIL.Image.Image): Colormap blended over original image.
            - boxes_overlay (PIL.Image.Image): Original image with annotated bounding boxes.
            - binary_mask (np.ndarray): Binary uint8 mask of suspicious regions (255=suspicious).
            - bounding_boxes (List[Dict[str, int]]): Coordinates for detected anomalies.
    """
    # Ensure RGB
    if original_image.mode != "RGB":
        original_image = original_image.convert("RGB")
    if ela_image.mode != "RGB":
        ela_image = ela_image.convert("RGB")

    orig_np = np.asarray(original_image)
    ela_np = np.asarray(ela_image)
    h, w = orig_np.shape[:2]

    # Compute grayscale intensity from amplified ELA image
    ela_gray = cv2.cvtColor(ela_np, cv2.COLOR_RGB2GRAY)

    # Adaptive smoothing: calculate kernel size proportional to image size (odd number >= 5)
    ksize = max(7, int(min(w, h) * 0.03))
    if ksize % 2 == 0:
        ksize += 1
    smoothed = cv2.GaussianBlur(ela_gray, (ksize, ksize), 0)

    # Normalize intensity to 0..255 range for colormap rendering
    min_val, max_val = float(np.min(smoothed)), float(np.max(smoothed))
    if max_val > min_val:
        norm_intensity = ((smoothed - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
    else:
        norm_intensity = np.zeros_like(smoothed, dtype=np.uint8)

    # Select colormap (INFERNO as default cyber-forensics theme, fallback to JET)
    cv_cmap = cv2.COLORMAP_INFERNO
    if colormap_type.upper() == "JET":
        cv_cmap = cv2.COLORMAP_JET

    heatmap_bgr = cv2.applyColorMap(norm_intensity, cv_cmap)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    # Ensure dimensions match
    if heatmap_rgb.shape[:2] != (h, w):
        heatmap_rgb = cv2.resize(heatmap_rgb, (w, h), interpolation=cv2.INTER_LINEAR)

    # Alpha blend colormap over the original image
    clamped_alpha = max(0.1, min(0.9, alpha))
    blended = cv2.addWeighted(orig_np, 1.0 - clamped_alpha, heatmap_rgb, clamped_alpha, 0)
    heatmap_overlay = Image.fromarray(blended, mode="RGB")

    # Detect suspicious regions
    bounding_boxes: List[Dict[str, int]] = []
    boxes_overlay_np = orig_np.copy()

    # Threshold on normalized intensity: identify the highest-intensity glowing zones
    norm_mean = float(np.mean(norm_intensity))
    norm_std = float(np.std(norm_intensity))
    thresh_val = int(max(135, min(220, norm_mean + 2.0 * norm_std)))
    _, raw_mask = cv2.threshold(norm_intensity, thresh_val, 255, cv2.THRESH_BINARY)

    # Morphological closing to group nearby components of an anomaly
    morph_k = max(7, int(min(w, h) * 0.025))
    if morph_k % 2 == 0:
        morph_k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_k, morph_k))
    binary_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Minimum bounding box area: at least 0.5% of total image area
    min_box_area = max(120, int(w * h * 0.005))
    max_box_area = int(w * h * 0.70)

    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_box_area <= area <= max_box_area:
            valid_contours.append((cnt, area))

    valid_contours.sort(key=lambda item: item[1], reverse=True)

    # Top 6 most prominent suspicious regions
    for idx, (cnt, area) in enumerate(valid_contours[:6]):
        x, y, bw, bh = cv2.boundingRect(cnt)
        bounding_boxes.append({
            "region_id": idx + 1,
            "x": int(x),
            "y": int(y),
            "width": int(bw),
            "height": int(bh),
            "area": int(area)
        })

        # Semi-transparent tinted highlight inside ROI
        sub_overlay = boxes_overlay_np.copy()
        cv2.rectangle(sub_overlay, (x, y), (x + bw, y + bh), (0, 240, 255), -1)
        cv2.addWeighted(sub_overlay, 0.20, boxes_overlay_np, 0.80, 0, boxes_overlay_np)

        # Crisp HUD rectangle
        cv2.rectangle(boxes_overlay_np, (x, y), (x + bw, y + bh), (0, 240, 255), 2)

        # Corner brackets for tactical cyber aesthetic
        corner_len = max(6, min(18, int(min(bw, bh) * 0.25)))
        cv2.line(boxes_overlay_np, (x, y), (x + corner_len, y), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x, y), (x, y + corner_len), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x + bw, y), (x + bw - corner_len, y), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x + bw, y), (x + bw, y + corner_len), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x, y + bh), (x + corner_len, y + bh), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x, y + bh), (x, y + bh - corner_len), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x + bw, y + bh), (x + bw - corner_len, y + bh), (255, 60, 90), 3)
        cv2.line(boxes_overlay_np, (x + bw, y + bh), (x + bw, y + bh - corner_len), (255, 60, 90), 3)

        # Label tag
        label_text = f"ROI #{idx + 1}"
        text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        label_bg_y1 = max(0, y - text_size[1] - 8)
        label_bg_y2 = y
        cv2.rectangle(boxes_overlay_np, (x, label_bg_y1), (x + text_size[0] + 10, label_bg_y2), (10, 16, 26), -1)
        cv2.rectangle(boxes_overlay_np, (x, label_bg_y1), (x + text_size[0] + 10, label_bg_y2), (0, 240, 255), 1)
        cv2.putText(
            boxes_overlay_np,
            label_text,
            (x + 5, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 240, 255),
            1,
            cv2.LINE_AA
        )

    boxes_overlay = Image.fromarray(boxes_overlay_np, mode="RGB")
    logger.debug(f"Detected {len(bounding_boxes)} suspicious regions")

    return heatmap_overlay, boxes_overlay, binary_mask, bounding_boxes
