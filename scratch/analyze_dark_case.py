import cv2
import numpy as np
import os

video_path = r"D:\Sandbox\chinhsuavideodc\samples\LogiCapture\2026-07-22_ĐC-C33-A1.1.mp4"
output_dir = r"C:\Users\tvn183660\.gemini\antigravity-ide\brain\76fb223f-651a-4096-8ee5-076e0f3b18ca\scratch"
os.makedirs(output_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, 60) # Frame 60
ret, frame = cap.read()
cap.release()

if not ret or frame is None:
    print("Error reading frame")
    exit(1)

# Save raw frame
cv2.imwrite(os.path.join(output_dir, "raw_frame.png"), frame)

# Analyze dark region pixel values
# Middle machine black body approx ROI: y: 350..850, x: 450..850
dark_roi = frame[350:850, 450:850]
gray_dark = cv2.cvtColor(dark_roi, cv2.COLOR_BGR2GRAY)

print("--- DARK ROI PIXEL STATS ---")
print(f"Min luminance: {np.min(gray_dark)}")
print(f"Max luminance: {np.max(gray_dark)}")
print(f"Mean luminance: {np.mean(gray_dark):.2f}")
print(f"Median luminance: {np.median(gray_dark):.2f}")
print(f"10th percentile: {np.percentile(gray_dark, 10):.2f}")
print(f"90th percentile: {np.percentile(gray_dark, 90):.2f}")

# 1. Method 1: Photoshop-style Shadow/Highlight Lift Algorithm
def shadow_highlight_lift(img, shadow_amount=0.8, shadow_width=0.5, radius=30):
    # Convert to LAB
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_float = l.astype(np.float32) / 255.0

    # Gaussian blur of L channel to estimate local illumination
    ksize = radius * 2 + 1
    blur_l = cv2.GaussianBlur(l_float, (ksize, ksize), 0)

    # Shadow mask: pixels darker than local/global threshold
    shadow_mask = np.power(1.0 - blur_l, 2.0)

    # Lift shadows
    lift = shadow_amount * shadow_mask * (1.0 - l_float)
    l_boosted = l_float + lift
    l_boosted = np.clip(l_boosted * 255.0, 0, 255).astype(np.uint8)

    # Apply CLAHE to boosted L channel
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_boosted)

    enhanced_lab = cv2.merge((l_enhanced, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

# 2. Method 2: Aggressive Multi-Scale Exposure Gain + Gamma Curve + Lift Offset
def aggressive_dark_lift(img, gain=3.5, offset=45, gamma=0.35):
    # Convert to LAB
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_float = l.astype(np.float32) / 255.0

    # Non-linear gain targeting dark areas
    # For dark pixels (l_float close to 0), boost heavily
    shadow_weight = np.clip(1.0 - l_float * 1.5, 0.0, 1.0)
    
    # Lift offset for black floor
    lift = (offset / 255.0) * shadow_weight
    
    # Gamma power
    gamma_l = np.power(l_float, gamma) * gain * shadow_weight + l_float * (1.0 - shadow_weight)
    l_out = np.clip((gamma_l + lift) * 255.0, 0, 255).astype(np.uint8)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_out)

    enhanced_lab = cv2.merge((l_clahe, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

# 3. Method 3: Multi-Scale Retinex (MSR)
def multi_scale_retinex(img, sigma_list=[15, 80, 250]):
    img_float = img.astype(np.float32) + 1.0
    retinex = np.zeros_like(img_float)
    for sigma in sigma_list:
        blur = cv2.GaussianBlur(img_float, (0, 0), sigma)
        retinex += np.log10(img_float) - np.log10(blur)
    retinex = retinex / len(sigma_list)
    
    # Normalize to 0-255
    for i in range(3):
        retinex[:, :, i] = (retinex[:, :, i] - np.min(retinex[:, :, i])) / (np.max(retinex[:, :, i]) - np.min(retinex[:, :, i])) * 255.0
    return np.clip(retinex, 0, 255).astype(np.uint8)

m1 = shadow_highlight_lift(frame)
m2 = aggressive_dark_lift(frame)
m3 = multi_scale_retinex(frame)

cv2.imwrite(os.path.join(output_dir, "test_shadow_lift.png"), m1)
cv2.imwrite(os.path.join(output_dir, "test_aggressive_lift.png"), m2)
cv2.imwrite(os.path.join(output_dir, "test_retinex.png"), m3)

print("Saved test images to scratch dir.")
