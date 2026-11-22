"""
ela.py - Error Level Analysis (ELA) Core Engine for ForensiScan
Generates resaved JPEG difference and amplifies compression artifacts.
"""

import io
import logging
from typing import List, Tuple, Union
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def generate_ela(
    image: Union[Image.Image, str, bytes, io.BytesIO],
    quality: int = 90,
    is_png: bool = False
) -> Tuple[Image.Image, np.ndarray, List[str], float, int]:
    """
    Perform Error Level Analysis (ELA) on an image.

    Args:
        image: PIL Image instance, path, bytes, or BytesIO stream.
        quality: JPEG compression quality for re-saving (default: 90).
        is_png: Flag indicating if the original file format was PNG.

    Returns:
        tuple containing:
            - ela_image (PIL.Image.Image): The auto-scaled amplified ELA image (RGB).
            - raw_diff (np.ndarray): Unscaled absolute pixel difference array (H, W, 3).
            - warnings (List[str]): Any diagnostic warnings generated.
            - scale (float): The amplification scale factor applied (255 / max_diff).
            - max_diff (int): Maximum absolute pixel difference observed.
    """
    warnings: List[str] = []

    # Open image if not already a PIL Image
    if not isinstance(image, Image.Image):
        if isinstance(image, (str, bytes)):
            if isinstance(image, bytes):
                image = io.BytesIO(image)
            image = Image.open(image)
        else:
            image = Image.open(image)

    # Detect PNG format or RGBA mode
    original_format = (image.format or "").upper()
    if is_png or original_format == "PNG" or image.mode in ("RGBA", "LA", "P"):
        warnings.append("PNG is lossless, so ELA is less reliable")

    # Convert to RGB (standard 24-bit color)
    if image.mode != "RGB":
        logger.debug(f"Converting image from mode {image.mode} to RGB")
        image_rgb = image.convert("RGB")
    else:
        image_rgb = image

    # Re-save as JPEG at fixed quality into an in-memory buffer
    resaved_buffer = io.BytesIO()
    image_rgb.save(resaved_buffer, format="JPEG", quality=quality)
    resaved_buffer.seek(0)
    resaved_image = Image.open(resaved_buffer)

    # Compute absolute difference between original and re-saved images
    orig_np = np.asarray(image_rgb, dtype=np.int16)
    resaved_np = np.asarray(resaved_image, dtype=np.int16)
    raw_diff = np.abs(orig_np - resaved_np).astype(np.uint8)

    # Calculate maximum difference and auto-scale amplification factor
    max_diff = int(np.max(raw_diff))
    if max_diff > 0:
        scale = 255.0 / float(max_diff)
    else:
        scale = 1.0

    # Amplify difference by auto-scale (255 / max)
    amplified_diff = np.clip(raw_diff.astype(np.float32) * scale, 0, 255).astype(np.uint8)
    ela_image = Image.fromarray(amplified_diff, mode="RGB")

    logger.debug(f"ELA completed: quality={quality}, max_diff={max_diff}, scale={scale:.2f}")
    return ela_image, raw_diff, warnings, scale, max_diff
