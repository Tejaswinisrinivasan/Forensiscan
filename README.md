# ForensiScan (Prototype v1)

**ForensiScan** is a lightweight, responsive digital image forensics web application engineered for hackathon demonstrations. It analyzes image tampering and splicing using **Error Level Analysis (ELA)**, **thermal colormap projection (INFERNO)**, and **deterministic heuristic anomaly scoring**.

> ⚠️ **Investigative Disclaimer:** ELA is an investigative clue, not conclusive proof of digital tampering. Natural sharp edges, high-contrast text, and textured surfaces can also glow due to standard DCT high-frequency quantization.

---

## ⚡ Features & Capabilities

- **Error Level Analysis (ELA) Engine (`ela.py`)**: Re-saves images at a known baseline JPEG compression quality ($Q=90$), computes the per-pixel absolute difference, and auto-scales the residual dynamic range ($255 / \text{max}$). Automatically converts PNG/RGBA to RGB and warns that lossless formats are less reliable for ELA.
- **Thermal Heatmap & ROI Detector (`heatmap.py`)**: Gaussian-smoothes the residual intensity, applies a high-contrast **INFERNO** colormap, resizes to original dimensions, alpha-blends (52%) over the original image, and isolates suspicious anomaly clusters with tactical bounding boxes.
- **ELA Heuristic Scoring Engine (`score.py`)**: Computes a deterministic suspicion score ($0.00$ to $1.00$) evaluating spatial concentration, peak-to-background ratio, high-error pixel share, and isolated anomaly counts. Categorized strictly as **"Low suspicion"**, **"Medium suspicion"**, or **"High suspicion"** (explicitly avoiding false certainty claims like "Authentic" or "Tampered").
- **Single-Page Forensic HUD (`static/index.html`, `css/style.css`, `js/main.js`)**:
  - Dark **cyber-forensics** tactical theme with HUD radar and scanline aesthetics.
  - Drag-and-drop upload with image preview and 1-click test sample loaders.
  - SVG radial score gauge with color transitions.
  - Processing latency indicator with `< 2 s Target Met ✓` badge (typically ~60–120 ms).
  - **4-Way Multi-Spectral Inspection Grid**: Original Image | Amplified ELA Map | Heatmap Overlay | Highlighted ROIs.
  - **Interactive Comparison Split-Slider**: Wipes smoothly between Original and Forensic Overlay.
  - **Print / PDF Dossier**: `window.print()` formatted via dedicated `@media print` CSS for instant executive forensic reports.
- **REST API (`app.py`)**:
  - `GET /`: Serves the single-page web UI.
  - `GET /api/health`: Returns service health and model development status (`{"status":"ok","cnn_model":"in training"}`).
  - `POST /api/analyze`: Accepts multipart form image uploads (JPEG/PNG up to 10 MB), rejects GIFs/videos with explicit 400 errors, and returns JSON with Base64 rendered images, suspicion metrics, and warnings.

---

## 📁 Project Architecture

```
forensiscan-antigravity/
├── app.py                # Flask application, routing, error handling & input validation
├── ela.py                # Core Error Level Analysis generator (JPEG Q=90 resave & auto-scale)
├── heatmap.py            # Gaussian smoothing, INFERNO colormap & bounding box ROI clustering
├── score.py              # Rule-based ELA heuristic scoring engine (0.00 to 1.00)
├── generate_samples.py   # Generates sample authentic, spliced, PNG, and low-res demo images
├── test_pipeline.py      # Standalone pipeline unit test
├── verify_server.py      # Automated 9-scenario API and endpoint verification suite
├── requirements.txt      # Python dependencies (Flask, Pillow, OpenCV, NumPy, Werkzeug)
├── README.md             # Documentation and quickstart guide
└── static/
    ├── index.html        # Forensic single-page UI
    ├── css/
    │   └── style.css     # Cyber-forensics dark theme, HUD widgets & @media print styles
    ├── js/
    │   └── main.js       # Client controller: drag-and-drop, SVG gauge, split comparison slider
    └── samples/          # Pre-packaged demo images for 1-click testing
        ├── authentic.jpg # Authentic control JPEG
        ├── tampered.jpg  # Spliced JPEG with anomalous patch
        ├── sample_lossless.png # PNG image (triggers lossless warning)
        └── sample_lowres.jpg   # Low-resolution image (triggers low-res warning)
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ (Python 3.10+ recommended)
- `pip` package manager

### 2. Installation
Clone or navigate to the project directory and install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3. Start the Web Server
Launch the Flask development server:

```bash
python app.py
```

### 4. Access the Application
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🧪 Verification & Testing

ForensiScan includes an automated test suite verifying all 9 core functional criteria:

```bash
python verify_server.py
```

### What `verify_server.py` tests:
1. `GET /` serves the UI HTML.
2. `GET /api/health` returns `{"status":"ok", "cnn_model":"in training"}`.
3. `POST /api/analyze` processes authentic JPEG with "Low suspicion" score.
4. `POST /api/analyze` detects spliced JPEG anomaly with "High suspicion" score.
5. `POST /api/analyze` detects PNG uploads and triggers `"PNG is lossless, so ELA is less reliable"`.
6. `POST /api/analyze` detects low-resolution images (< 300px) and emits a low-resolution warning.
7. `POST /api/analyze` rejects GIF uploads with HTTP 400 and an informative error message.
8. `POST /api/analyze` rejects video files (e.g. `.mp4`) with HTTP 400.
9. Static file routing for `/css/style.css`, `/js/main.js`, and sample images.

---

## 📡 API Reference

### 1. Health Check
```http
GET /api/health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "cnn_model": "in training",
  "prototype_version": "v1.0.0",
  "core_engine": "Error Level Analysis (ELA) + Rule-based Heuristic",
  "supported_formats": ["JPEG", "JPG", "PNG"],
  "max_upload_size_mb": 10
}
```

### 2. Forensic Analysis
```http
POST /api/analyze
Content-Type: multipart/form-data
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `image` | File | Yes | JPEG or PNG image file (max 10 MB) |

**Sample Response (200 OK):**
```json
{
  "status": "success",
  "original_image": "data:image/jpeg;base64,...",
  "ela_image": "data:image/png;base64,...",
  "heatmap_overlay": "data:image/png;base64,...",
  "boxes_overlay": "data:image/png;base64,...",
  "suspicion_score": 0.72,
  "heuristic_label": "High suspicion",
  "processing_time_ms": 109.32,
  "target_time_met": true,
  "warnings": [],
  "image_info": {
    "filename": "tampered.jpg",
    "detected_format": "JPEG",
    "width": 800,
    "height": 500,
    "resolution": "800 x 500",
    "file_size_kb": 84.2,
    "color_mode": "RGB",
    "channels": 3,
    "ela_resave_quality": 90,
    "ela_amplification_scale": 6.22,
    "max_pixel_difference": 41,
    "detected_regions_count": 1
  },
  "bounding_boxes": [
    {
      "region_id": 1,
      "x": 490,
      "y": 70,
      "width": 250,
      "height": 170,
      "area": 14598
    }
  ],
  "score_details": {
    "metric_type": "ELA heuristic score (rule-based statistical analysis)",
    "mean_intensity": 0.35,
    "max_intensity": 41,
    "std_intensity": 1.48,
    "high_pixel_ratio_pct": 1.52,
    "spatial_concentration_ratio": 8.13,
    "peak_to_mean_ratio": 23.46,
    "detected_roi_count": 1,
    "is_machine_learning": false,
    "model_architecture": "Deterministic heuristic (CNN in training)"
  },
  "disclaimer": "ELA is a clue, not proof of tampering. Sharp edges and texture can also glow."
}
```

---

## 🔍 How Error Level Analysis Works

```
[Input Image] ──> [Re-save as JPEG @ Q=90] ──> [Subtract: |Original - Resaved|] ──> [Amplify: 255 / max]
```

1. **Re-save**: The image is re-compressed as JPEG at a fixed quality factor ($Q=90$). An authentic image already compressed at a uniform quality level will experience minimal additional quantization loss across uniform regions.
2. **Subtract**: The per-pixel absolute difference is computed between the original and re-saved images to isolate compression residual errors.
3. **Amplify**: Residual differences are auto-scaled across the full 0–255 dynamic range to make subtle compression disparities clearly visible.

---

## 🧭 Scope & Limitations

| Aspect | In Scope (v1.0) | Out of Scope (v1.0) |
|---|---|---|
| **Media Formats** | Static JPEG and PNG (up to 10 MB) | Videos (MP4/AVI), Animated GIFs, WebP |
| **Analysis Scope** | Single-image Error Level Analysis & Heatmap | Multi-frame temporal video forensics |
| **Detection Method** | Deterministic statistical heuristic | Trained Machine Learning / Deep Learning model |
| **Image Resolution** | High- & medium-res camera / web images | Low-res social media memes (< 300px) |
| **Infrastructure** | Lightweight local Flask server | Multi-tenant cloud with user authentication |

---

## 🗺️ Roadmap to v2.0

- **Week 1–2: CNN Model Training**: Train a convolutional neural network on CASIA v2 and CoMoFoD tampering benchmarks.
- **Week 3: Model & Pipeline Integration**: Export ONNX model weights and integrate dual-engine inference (ELA + CNN ensemble) into the Flask API.
- **Week 4: False Positive Calibration**: Test against challenging high-contrast natural textures (architectural grates, foliage, high-ISO sensor noise).
- **Week 5: Cloud Deployment & Final Demo**: Docker containerization, Google Cloud Run deployment, and automated PDF forensic dossier generation.
