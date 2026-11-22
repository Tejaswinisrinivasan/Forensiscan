"""
test_pipeline.py - Validate the ELA pipeline on sample images
"""

from PIL import Image
from ela import generate_ela
from heatmap import generate_heatmap_and_boxes
from score import calculate_ela_score


def run_tests():
    samples = [
        "authentic.jpg",
        "tampered.jpg",
        "sample_lossless.png",
        "sample_lowres.jpg"
    ]

    for name in samples:
        filepath = f"static/samples/{name}"
        img = Image.open(filepath)
        is_png = name.endswith(".png")

        ela_img, raw_diff, warnings, scale, max_diff = generate_ela(img, 90, is_png=is_png)
        h_overlay, b_overlay, mask, boxes = generate_heatmap_and_boxes(img, ela_img)
        score, label, details = calculate_ela_score(raw_diff, None, boxes)

        print(f"=== {name} ===")
        print(f"  Score: {score:.2f} ({label})")
        print(f"  Scale Factor: {scale:.2f} | Max Diff: {max_diff}")
        print(f"  Detected ROIs: {len(boxes)}")
        print(f"  Concentration Ratio: {details.get('spatial_concentration_ratio')}")
        print(f"  Peak/Mean Ratio: {details.get('peak_to_mean_ratio')}")
        print(f"  Warnings: {warnings}")
        print()


if __name__ == "__main__":
    run_tests()
