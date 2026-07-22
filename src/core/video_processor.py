"""
Module VideoProcessor - Lớp Model quản lý toàn bộ xử lý video và hình ảnh.
Nằm trong package src.core.
"""

import os
import sys
from typing import Callable, Optional, Tuple, Dict, Any
import cv2
import numpy as np


class ProcessingMode:
    """Các chế độ che/xóa đối tượng hỗ trợ."""
    INPAINT = "inpaint"
    MASK = "mask"
    BLUR = "blur"
    CROP = "crop"

    ALL_MODES = [INPAINT, MASK, BLUR, CROP]


class VideoProcessor:
    """Class xử lý video core sử dụng OpenCV và Object Tracking."""

    @staticmethod
    def get_video_info(video_path: str) -> Dict[str, Any]:
        """Lấy thông tin kỹ thuật cơ bản của file video."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"File video không tồn tại: '{video_path}'")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Không thể mở file video: '{video_path}'")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0.0

        cap.release()
        return {
            "path": video_path,
            "width": width,
            "height": height,
            "fps": fps,
            "total_frames": total_frames,
            "duration_sec": duration_sec
        }

    @staticmethod
    def create_tracker(frame: np.ndarray, roi: Tuple[int, int, int, int]):
        """Khởi tạo MIL Object Tracker từ OpenCV."""
        try:
            tracker = cv2.TrackerMIL_create()
            tracker.init(frame, roi)
            return tracker
        except cv2.error as err:
            sys.stderr.write(f"Cảnh báo: Không thể khởi tạo TrackerMIL: {err}\n")
            return None

    @staticmethod
    def process_single_frame(
        frame: np.ndarray,
        mode: str,
        roi: Tuple[int, int, int, int],
        tracker: Optional[Any] = None,
        padding: int = 10
    ) -> np.ndarray:
        """
        Xử lý 1 khung hình đơn lẻ dựa theo chế độ mode và tọa độ ROI / Tracker.
        """
        height, width = frame.shape[:2]

        if mode == ProcessingMode.CROP:
            crop_w = roi[0] if roi else int(width * 0.8)
            crop_w = max(1, min(crop_w, width))
            return frame[0:height, 0:crop_w]

        tracked_box = roi
        if tracker is not None:
            try:
                success, box = tracker.update(frame)
                if success:
                    bx, by, bw, bh = [int(v) for v in box]
                    bx = max(0, bx - padding)
                    by = max(0, by - padding)
                    bw = min(width - bx, bw + 2 * padding)
                    bh = min(height - by, bh + 2 * padding)
                    tracked_box = (bx, by, bw, bh)
            except cv2.error:
                tracked_box = roi

        bx, by, bw, bh = tracked_box
        out_frame = frame.copy()

        if mode == ProcessingMode.INPAINT:
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[by:by+bh, bx:bx+bw] = 255
            out_frame = cv2.inpaint(
                frame, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA
            )

        elif mode == ProcessingMode.MASK:
            out_frame[by:by+bh, bx:bx+bw] = (30, 30, 30)

        elif mode == ProcessingMode.BLUR:
            sub = out_frame[by:by+bh, bx:bx+bw]
            if sub.size > 0:
                blurred = cv2.GaussianBlur(sub, (99, 99), 30)
                out_frame[by:by+bh, bx:bx+bw] = blurred

        return out_frame

    @classmethod
    def process_video(
        cls,
        video_path: str,
        output_path: Optional[str] = None,
        mode: str = ProcessingMode.INPAINT,
        roi: Optional[Tuple[int, int, int, int]] = None,
        padding: int = 10,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        stop_checker: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Vòng lặp chính xử lý video xuất ra file kết quả. Hỗ trợ cắt/chọn khoảng thời gian (start_time -> end_time).
        Tự động lưu vào thư mục outputs/ nếu output_path không được truyền vào.
        """
        info = cls.get_video_info(video_path)
        width = info["width"]
        height = info["height"]
        fps = info["fps"]
        total_frames = info["total_frames"]

        start_frame = max(0, int(start_time * fps)) if fps > 0 else 0
        if end_time is not None and end_time > start_time:
            end_frame = min(total_frames, int(end_time * fps)) if fps > 0 else total_frames
        else:
            end_frame = total_frames

        target_frames = max(1, end_frame - start_frame)

        if output_path is None:
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.basename(video_path)
            base_name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{base_name}_{mode}_processed.mp4")

        cap = cv2.VideoCapture(video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        if mode == ProcessingMode.CROP:
            out_w = roi[0] if roi else int(width * 0.8)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, height))
        else:
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        tracker = None
        if mode != ProcessingMode.CROP and roi is not None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            ret, init_frame = cap.read()
            if ret and init_frame is not None:
                tracker = cls.create_tracker(init_frame, roi)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current_frame_pos = start_frame
        processed_count = 0

        try:
            while cap.isOpened() and current_frame_pos < end_frame:
                if stop_checker and stop_checker():
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                current_frame_pos += 1
                processed_count += 1

                out_frame = cls.process_single_frame(
                    frame=frame,
                    mode=mode,
                    roi=roi if roi else (0, 0, width, height),
                    tracker=tracker,
                    padding=padding
                )
                writer.write(out_frame)

                if progress_callback:
                    pct = (processed_count / target_frames) * 100.0
                    progress_callback(pct, processed_count, target_frames)

        finally:
            cap.release()
            writer.release()

        return output_path
