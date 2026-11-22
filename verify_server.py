"""
verify_server.py - Automated end-to-end test suite for ForensiScan
Starts Flask in a background thread or process, exercises all endpoints, and verifies response schemas.
"""

import io
import json
import os
import sys
import threading
import time
import requests
from app import app


def run_tests():
    print(">>> Starting ForensiScan test suite...")
    client = app.test_client()

    # Test 1: GET / serves the UI
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200 for /, got {res.status_code}"
    assert b"ForensiScan" in res.data or b"FORENSISCAN" in res.data, "UI title missing from index.html"
    print("✔ GET / successfully serves the UI HTML")

    # Test 2: GET /api/health returns {"status":"ok","cnn_model":"in training"}
    res = client.get("/api/health")
    assert res.status_code == 200, f"Expected 200 for /api/health, got {res.status_code}"
    health_data = json.loads(res.data)
    assert health_data.get("status") == "ok", f"Expected status 'ok', got {health_data}"
    assert health_data.get("cnn_model") == "in training", f"Expected cnn_model 'in training', got {health_data}"
    print(f"✔ GET /api/health returned: {health_data}")

    # Test 3: POST /api/analyze with sample authentic JPEG
    auth_path = os.path.join("static", "samples", "authentic.jpg")
    with open(auth_path, "rb") as f:
        auth_bytes = f.read()

    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(auth_bytes), "authentic.jpg")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 200, f"Expected 200 for analyze, got {res.status_code}: {res.data}"
    data_auth = json.loads(res.data)
    assert "ela_image" in data_auth, "Missing ela_image"
    assert "heatmap_overlay" in data_auth, "Missing heatmap_overlay"
    assert "boxes_overlay" in data_auth, "Missing boxes_overlay"
    assert "suspicion_score" in data_auth, "Missing suspicion_score"
    assert "heuristic_label" in data_auth, "Missing heuristic_label"
    assert "processing_time_ms" in data_auth, "Missing processing_time_ms"
    assert "warnings" in data_auth, "Missing warnings"
    assert "image_info" in data_auth, "Missing image_info"
    assert data_auth["heuristic_label"] in ["Low suspicion", "Medium suspicion", "High suspicion"], \
        f"Invalid label: {data_auth['heuristic_label']}"
    print(f"✔ POST /api/analyze on authentic.jpg: score={data_auth['suspicion_score']}, "
          f"label='{data_auth['heuristic_label']}', time={data_auth['processing_time_ms']} ms")

    # Test 4: POST /api/analyze with sample tampered JPEG
    tamp_path = os.path.join("static", "samples", "tampered.jpg")
    with open(tamp_path, "rb") as f:
        tamp_bytes = f.read()

    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(tamp_bytes), "tampered.jpg")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 200, f"Expected 200 for analyze, got {res.status_code}"
    data_tamp = json.loads(res.data)
    assert data_tamp["heuristic_label"] in ["Low suspicion", "Medium suspicion", "High suspicion"]
    print(f"✔ POST /api/analyze on tampered.jpg: score={data_tamp['suspicion_score']}, "
          f"label='{data_tamp['heuristic_label']}', ROIs={len(data_tamp.get('bounding_boxes', []))}")

    # Test 5: POST /api/analyze with lossless PNG (must trigger PNG warning)
    png_path = os.path.join("static", "samples", "sample_lossless.png")
    with open(png_path, "rb") as f:
        png_bytes = f.read()

    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(png_bytes), "sample_lossless.png")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 200
    data_png = json.loads(res.data)
    assert any("PNG is lossless, so ELA is less reliable" in w for w in data_png["warnings"]), \
        f"Expected PNG warning, got {data_png['warnings']}"
    print(f"✔ POST /api/analyze on PNG triggered warning: {data_png['warnings']}")

    # Test 6: POST /api/analyze with low-res image (must trigger low-res warning)
    lowres_path = os.path.join("static", "samples", "sample_lowres.jpg")
    with open(lowres_path, "rb") as f:
        lowres_bytes = f.read()

    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(lowres_bytes), "sample_lowres.jpg")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 200
    data_lowres = json.loads(res.data)
    assert any("resolution is very small" in w for w in data_lowres["warnings"]), \
        f"Expected low-res warning, got {data_lowres['warnings']}"
    print(f"✔ POST /api/analyze on low-res image triggered warning: {data_lowres['warnings']}")

    # Test 7: POST /api/analyze with rejected GIF format
    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(b"GIF89a fake gif data"), "animation.gif")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 400, f"Expected 400 for GIF, got {res.status_code}"
    gif_err = json.loads(res.data)
    assert "Unsupported file format" in gif_err.get("error", ""), f"Unexpected error message: {gif_err}"
    print(f"✔ POST /api/analyze on GIF cleanly rejected with 400: {gif_err['error']}")

    # Test 8: POST /api/analyze with rejected video format
    res = client.post(
        "/api/analyze",
        data={"image": (io.BytesIO(b"fake mp4 video bytes"), "clip.mp4")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 400
    mp4_err = json.loads(res.data)
    print(f"✔ POST /api/analyze on MP4 cleanly rejected with 400: {mp4_err['error']}")

    # Test 9: Verify static files
    res = client.get("/css/style.css")
    assert res.status_code == 200, f"Expected 200 for /css/style.css, got {res.status_code}"
    res = client.get("/js/main.js")
    assert res.status_code == 200, f"Expected 200 for /js/main.js, got {res.status_code}"
    res = client.get("/samples/authentic.jpg")
    assert res.status_code == 200, f"Expected 200 for /samples/authentic.jpg, got {res.status_code}"
    print("✔ Static assets (/css/style.css, /js/main.js, /samples/authentic.jpg) served successfully")

    print("\n🎉 ALL 9 AUTOMATED TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
