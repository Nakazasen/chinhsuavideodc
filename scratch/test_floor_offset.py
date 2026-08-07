import cv2
import numpy as np
import os

video_path = r"D:\Sandbox\chinhsuavideodc\samples\LogiCapture\2026-07-22_ĐC-C33-A1.1.mp4"
output_dir = r"C:\Users\tvn183660\.gemini\antigravity-ide\brain\76fb223f-651a-4096-8ee5-076e0f3b18ca\scratch"

cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
ret, frame = cap.read()
cap.release()

def super_dark_boost(img, offset_val=80.0, contrast_val=2.5, gamma_val=0.4):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_float = l.astype(np.float32)

    # Formula: L_new = offset + (255 - offset) * (L / 255)^gamma
    norm_l = l_float / 255.0
    l_new = offset_val + (255.0 - offset_val) * np.power(norm_l, gamma_val)
    
    # Adaptive local contrast via CLAHE on l_new
    l_new = np.clip(l_new, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=6.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_new)

    # Blend a & b color channels slightly boosted to restore color in darks
    enhanced_lab = cv2.merge((l_clahe, a, b))
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Sharpening
    blurred = cv2.GaussianBlur(enhanced_bgr, (0, 0), 1.5)
    enhanced_bgr = cv2.addWeighted(enhanced_bgr, 1.4, blurred, -0.4, 0)
    return np.clip(enhanced_bgr, 0, 255).astype(np.uint8)

# Test with offset 60, 90, 120
t60 = super_dark_boost(frame, offset_val=60.0)
t90 = super_dark_boost(frame, offset_val=90.0)
t120 = super_dark_boost(frame, offset_val=120.0)

cv2.imwrite(os.path.join(output_dir, "super_boost_offset60.png"), t60)
cv2.imwrite(os.path.join(output_dir, "super_boost_offset90.png"), t90)
cv2.imwrite(os.path.join(output_dir, "super_boost_offset120.png"), t120)

# Check dark region pixel stats after offset 90
dark_roi = t90[350:850, 450:850]
gray_dark = cv2.cvtColor(dark_roi, cv2.COLOR_BGR2GRAY)
print("--- AFTER OFFSET 90 STATS ---")
print(f"Min luminance: {np.min(gray_dark)}")
print(f"Max luminance: {np.max(gray_dark)}")
print(f"Mean luminance: {np.mean(gray_dark):.2f}")
print(f"Median luminance: {np.median(gray_dark):.2f}")
