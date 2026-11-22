"""
app.py - ForensiScan Prototype v1 Flask Application
Image Tampering Analysis using Error Level Analysis (ELA) for Hackathon Demo.
"""

import base64
import io
import logging
import os
import time
from typing import Dict, Any, List

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

from ela import generate_ela
from heatmap import generate_heatmap_and_boxes
from score import calculate_ela_score

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("forensiscan")

# Initialize Flask application
app = Flask(__name__, static_folder="static", static_url_path="")

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False

# Allowed image extensions for prototype v1
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
REJECTED_EXTENSIONS = {"gif", "mp4", "avi", "mov", "mkv", "webm", "webp", "bmp", "tiff", "svg"}


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Extract file extension."""
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def pil_to_base64_data_url(img: Image.Image, format_name: str = "PNG") -> str:
    """Convert a PIL image to a Base64 data URL string."""
    buf = io.BytesIO()
    # Save as PNG for lossless display in browser
    img.save(buf, format=format_name)
    buf.seek(0)
    b64_encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if format_name.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64_encoded}"


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    logger.warning("Upload rejected: File size exceeded 10 MB limit")
    return jsonify({
        "error": "File size exceeds the 10 MB limit for ForensiScan prototype v1.",
        "max_size_mb": 10
    }), 413


@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"Internal server error: {e}", exc_info=True)
    return jsonify({"error": "An internal error occurred during forensic image processing."}), 500


@app.route("/")
def index():
    """Serve the ForensiScan single-page UI."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    Returns current service health and model development status.
    """
    return jsonify({
        "status": "ok",
        "cnn_model": "in training",
        "prototype_version": "v1.0.0",
        "core_engine": "Error Level Analysis (ELA) + Rule-based Heuristic",
        "supported_formats": ["JPEG", "JPG", "PNG"],
        "max_upload_size_mb": 10
    }), 200


@app.route("/api/analyze", methods=["POST"])
def analyze_image():
    """
    Perform forensic ELA analysis on an uploaded image.
    Accepts: multipart/form-data with file field 'image'.
    Returns: JSON with base64 images, ELA heuristic score, warnings, and metadata.
    """
    start_time = time.perf_counter()
    logger.info("Received image analysis request")

    # 1. Validate request payload
    if "image" not in request.files:
        logger.warning("Analysis rejected: Missing 'image' field in request")
        return jsonify({
            "error": "No image file provided. Please submit a file with field name 'image'."
        }), 400

    file = request.files["image"]
    if not file or file.filename.strip() == "":
        logger.warning("Analysis rejected: Empty filename")
        return jsonify({"error": "No file selected for analysis."}), 400

    filename = file.filename
    ext = get_file_extension(filename)

    # 2. Check for explicitly rejected formats (GIF, Video, etc.)
    if ext in REJECTED_EXTENSIONS:
        msg = (
            f"Unsupported file format '.{ext}'. ForensiScan prototype v1 strictly analyzes static "
            f"JPEG and PNG images. Videos, GIFs, and other media types are currently out of scope."
        )
        logger.warning(f"Analysis rejected: Unsupported format {ext}")
        return jsonify({"error": msg, "rejected_extension": ext}), 400

    if not allowed_file(filename):
        msg = (
            f"Invalid file type '.{ext}'. Only static JPEG and PNG formats (.jpg, .jpeg, .png) "
            f"are supported in ForensiScan prototype v1."
        )
        logger.warning(f"Analysis rejected: Not allowed file {filename}")
        return jsonify({"error": msg}), 400

    warnings: List[str] = []

    # 3. Read image and inspect metadata
    try:
        file_bytes = file.read()
        file_size_bytes = len(file_bytes)
        file_size_kb = round(file_size_bytes / 1024.0, 1)

        # Open image using Pillow
        image_stream = io.BytesIO(file_bytes)
        pil_image = Image.open(image_stream)
        detected_format = (pil_image.format or ext).upper()

        width, height = pil_image.size
        channels = len(pil_image.getbands())
        original_mode = pil_image.mode

        # Check for very small resolution (social media recompressed / low-res)
        if width < 300 or height < 300:
            warning_msg = (
                f"Image resolution is very small ({width}x{height}px). "
                f"Low-resolution and heavily compressed social media images reduce ELA diagnostic reliability."
            )
            warnings.append(warning_msg)
            logger.info(f"Low resolution warning: {width}x{height}")

        is_png_format = (detected_format == "PNG" or ext == "png")

        # 4. Generate Error Level Analysis
        ela_img, raw_diff, ela_warnings, scale_factor, max_diff = generate_ela(
            pil_image,
            quality=90,
            is_png=is_png_format
        )
        warnings.extend(ela_warnings)

        # 5. Generate Heatmap and Suspicious Region Bounding Boxes
        heatmap_overlay, boxes_overlay, binary_mask, bounding_boxes = generate_heatmap_and_boxes(
            original_image=pil_image,
            ela_image=ela_img,
            colormap_type="INFERNO",
            alpha=0.52
        )

        # 6. Compute ELA Heuristic Score
        suspicion_score, heuristic_label, score_details = calculate_ela_score(
            raw_diff=raw_diff,
            amplified_ela=np.asarray(ela_img),
            bounding_boxes=bounding_boxes
        )

        # 7. Encode images to Base64 data URLs for seamless client-side rendering
        # Also encode original image as standard RGB base64 to ensure consistent display
        original_rgb = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
        orig_base64 = pil_to_base64_data_url(original_rgb, "JPEG")
        ela_base64 = pil_to_base64_data_url(ela_img, "PNG")
        heatmap_base64 = pil_to_base64_data_url(heatmap_overlay, "PNG")
        boxes_base64 = pil_to_base64_data_url(boxes_overlay, "PNG")

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Image metadata summary
        image_info = {
            "filename": filename,
            "detected_format": detected_format,
            "width": width,
            "height": height,
            "resolution": f"{width} x {height}",
            "file_size_kb": file_size_kb,
            "color_mode": original_mode,
            "channels": channels,
            "ela_resave_quality": 90,
            "ela_amplification_scale": round(scale_factor, 2),
            "max_pixel_difference": max_diff,
            "detected_regions_count": len(bounding_boxes)
        }

        response_data: Dict[str, Any] = {
            "status": "success",
            "original_image": orig_base64,
            "ela_image": ela_base64,
            "heatmap_overlay": heatmap_base64,
            "boxes_overlay": boxes_base64,
            "suspicion_score": suspicion_score,
            "heuristic_label": heuristic_label,  # "Low / Medium / High suspicion", NOT "Authentic/Tampered"
            "score_details": score_details,
            "processing_time_ms": processing_time_ms,
            "target_time_met": processing_time_ms < 2000.0,
            "warnings": warnings,
            "image_info": image_info,
            "bounding_boxes": bounding_boxes,
            "disclaimer": "ELA is a clue, not proof of tampering. Sharp edges and texture can also glow."
        }

        logger.info(
            f"Analysis complete for {filename}: score={suspicion_score} ({heuristic_label}) "
            f"in {processing_time_ms} ms"
        )
        return jsonify(response_data), 200

    except UnidentifiedImageError:
        logger.warning(f"Failed to identify image format for {filename}")
        return jsonify({
            "error": "The uploaded file could not be recognized as a valid image. Ensure it is a valid JPEG or PNG."
        }), 400
    except Exception as exc:
        logger.error(f"Processing error during analysis: {exc}", exc_info=True)
        return jsonify({
            "error": f"An error occurred while analyzing the image: {str(exc)}"
        }), 500


if __name__ == "__main__":
    # Run locally on port 5000
    logger.info("Starting ForensiScan prototype v1 server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
