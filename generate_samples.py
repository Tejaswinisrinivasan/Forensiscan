"""
generate_samples.py - Generate realistic demo samples for ForensiScan
"""

import io
import os
import cv2
import numpy as np
from PIL import Image


def create_demo_samples():
    output_dir = os.path.join("static", "samples")
    os.makedirs(output_dir, exist_ok=True)
    w, h = 800, 500

    # Base image: realistic landscape with horizon, textures, and structures
    base_img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        ratio = y / float(h)
        b = int(210 * (1 - ratio) + 60 * ratio)
        g = int(170 * (1 - ratio) + 100 * ratio)
        r = int(100 * (1 - ratio) + 210 * ratio)
        base_img[y, :] = [r, g, b]

    # Ground
    cv2.rectangle(base_img, (0, 320), (w, h), (40, 55, 40), -1)
    cv2.circle(base_img, (200, 370), 160, (50, 70, 50), -1)
    cv2.circle(base_img, (620, 390), 200, (45, 65, 45), -1)

    # Buildings with windows
    cv2.rectangle(base_img, (100, 200), (220, 330), (85, 90, 100), -1)
    cv2.rectangle(base_img, (240, 160), (340, 340), (110, 115, 125), -1)
    cv2.rectangle(base_img, (360, 220), (450, 340), (75, 80, 90), -1)

    for bx, by, bw, bh in [(100, 200, 120, 130), (240, 160, 100, 180), (360, 220, 90, 120)]:
        for wx in range(bx + 12, bx + bw - 12, 20):
            for wy in range(by + 12, by + bh - 12, 24):
                cv2.rectangle(base_img, (wx, wy), (wx + 10, wy + 14), (230, 240, 150), -1)

    # Road
    cv2.rectangle(base_img, (0, 420), (w, h), (32, 35, 38), -1)
    for rx in range(30, w, 80):
        cv2.rectangle(base_img, (rx, 455), (rx + 45, 465), (235, 235, 235), -1)

    pil_base = Image.fromarray(base_img)

    # 1. Authentic JPEG: saved uniformly at quality 80
    authentic_path = os.path.join(output_dir, "authentic.jpg")
    pil_base.save(authentic_path, "JPEG", quality=80)
    print(f"Saved {authentic_path}")

    # 2. Tampered JPEG:
    # First degrade base at quality 65
    bg_buf = io.BytesIO()
    pil_base.save(bg_buf, "JPEG", quality=65)
    bg_buf.seek(0)
    bg_q65 = Image.open(bg_buf).convert("RGB")
    tampered_np = np.asarray(bg_q65).copy()

    # Spliced element: high-contrast radar dish / drone / badge with dense high-frequency grid
    px, py, pw, ph = 490, 70, 250, 170
    patch = np.full((ph, pw, 3), 245, dtype=np.uint8)
    # Dense cyber radar pattern
    cv2.circle(patch, (125, 85), 65, (20, 30, 180), 4)
    cv2.circle(patch, (125, 85), 45, (180, 20, 40), 3)
    cv2.circle(patch, (125, 85), 25, (20, 180, 40), 2)
    cv2.line(patch, (125, 10), (125, 160), (20, 30, 180), 2)
    cv2.line(patch, (50, 85), (200, 85), (20, 30, 180), 2)
    for i in range(10, pw - 10, 8):
        cv2.line(patch, (i, 130), (i, 160), (10, 10, 10), 1)

    cv2.putText(patch, "RESTRICTED", (40, 115), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 0, 160), 2)
    cv2.putText(patch, "[SPLICED ASSET]", (52, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

    tampered_np[py:py + ph, px:px + pw] = patch

    # Save as JPEG quality 85
    tampered_path = os.path.join(output_dir, "tampered.jpg")
    Image.fromarray(tampered_np).save(tampered_path, "JPEG", quality=85)
    print(f"Saved {tampered_path}")

    # 3. Lossless PNG
    png_path = os.path.join(output_dir, "sample_lossless.png")
    pil_base.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # 4. Low-res image
    lowres_pil = pil_base.resize((200, 140), Image.Resampling.LANCZOS)
    lowres_path = os.path.join(output_dir, "sample_lowres.jpg")
    lowres_pil.save(lowres_path, "JPEG", quality=75)
    print(f"Saved {lowres_path}")


if __name__ == "__main__":
    create_demo_samples()
