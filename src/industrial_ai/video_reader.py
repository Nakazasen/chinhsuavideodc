"""
Module Đọc và Trích xuất Metadata / Keyframes từ Video
"""

import os
import cv2
from typing import Dict, List, Tuple, Optional


class VideoReader:
    """Quản lý việc đọc file video, trích xuất metadata và lưu keyframes."""

    def __init__(self, video_path: str):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Không thể mở file video: {video_path}")

    def get_metadata(self) -> Dict[str, any]:
        """Trích xuất thông số kỹ thuật của video."""
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / fps if fps > 0 else 0.0

        return {
            "filepath": self.video_path,
            "filename": os.path.basename(self.video_path),
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration_sec": round(duration_sec, 2),
            "resolution": f"{width}x{height}"
        }

    def extract_keyframes(self, output_dir: str, interval_sec: float = 2.0) -> List[Dict[str, any]]:
        """
        Trích xuất các khung hình (Keyframes) định kỳ theo khoảng thời gian (giây).
        Trả về danh sách thông tin các ảnh đã lưu.
        """
        os.makedirs(output_dir, exist_ok=True)
        metadata = self.get_metadata()
        fps = metadata["fps"]
        frame_interval = max(1, int(fps * interval_sec))

        keyframes_info = []
        frame_idx = 0

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp_sec = round(frame_idx / fps, 2)
                filename = f"keyframe_{frame_idx:06d}_{timestamp_sec}s.jpg"
                save_path = os.path.join(output_dir, filename)
                cv2.imwrite(save_path, frame)

                keyframes_info.append({
                    "frame_index": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "image_path": save_path
                })

            frame_idx += 1

        return keyframes_info

    def release(self):
        """Giải phóng tài nguyên Capture."""
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
