"""
Module VideoProcessor - Lớp Model quản lý toàn bộ xử lý video và hình ảnh.
Nằm trong package src.core.
"""

import os
import sys
import datetime
import re
from typing import Callable, Optional, Tuple, Dict, Any, Union, List
import cv2
import numpy as np


class ProcessingMode:
    """Các chế độ che/xóa/chỉnh sửa đối tượng hỗ trợ."""
    INPAINT = "inpaint"
    MASK = "mask"
    BLUR = "blur"
    CROP = "crop"
    ENHANCE_LIGHT = "enhance_light"
    NONE = "none"

    ALL_MODES = [INPAINT, MASK, BLUR, CROP, ENHANCE_LIGHT, NONE]


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
    def get_video_start_datetime(video_path: str, duration_sec: float = 0.0) -> datetime.datetime:
        """
        Tự động xác định ngày giờ bắt đầu quay thực tế của video:
        - Phân tích ngày trong tên file (nếu có dạng YYYY-MM-DD).
        - Phân tích file mtime (thời gian lưu file) trừ đi tổng thời lượng video.
        """
        try:
            stat = os.stat(video_path)
            file_dt = datetime.datetime.fromtimestamp(stat.st_mtime)
            start_dt = file_dt - datetime.timedelta(seconds=duration_sec)
        except Exception:
            start_dt = datetime.datetime.now()

        try:
            fname = os.path.basename(video_path)
            m = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', fname)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                start_dt = start_dt.replace(year=y, month=mo, day=d)
        except Exception:
            pass

        return start_dt

    @staticmethod
    def format_timecode(seconds: float, show_millis: bool = True) -> str:
        """Đổi số giây sang định dạng HH:MM:SS.ms hoặc HH:MM:SS."""
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if show_millis:
            millis = int((seconds - int(seconds)) * 100)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:02d}"
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_realtime(
        start_datetime: datetime.datetime,
        elapsed_seconds: float,
        show_millis: bool = True
    ) -> str:
        """Đổi mốc thời gian thực sang chuỗi YYYY-MM-DD HH:MM:SS.ms"""
        if elapsed_seconds < 0:
            elapsed_seconds = 0.0
        cur_dt = start_datetime + datetime.timedelta(seconds=elapsed_seconds)
        dt_str = cur_dt.strftime("%Y-%m-%d %H:%M:%S")
        if show_millis:
            millis = int((elapsed_seconds - int(elapsed_seconds)) * 100)
            return f"{dt_str}.{millis:02d}"
        return dt_str

    @staticmethod
    def draw_timeline_overlay(
        frame: np.ndarray,
        current_time_sec: float,
        total_duration_sec: float = 0.0,
        timeline_mode: str = "elapsed",
        start_datetime: Optional[Union[datetime.datetime, str]] = None,
        position: str = "bottom_right",
        margin_x: int = 40,
        margin_y: int = 50,
        font_scale: float = 0.95,
        thickness: int = 2,
        show_millis: bool = True,
        show_total: bool = True
    ) -> np.ndarray:
        """
        Vẽ thanh OSD Timeline / Timecode ở góc chỉ định với nền đen mờ sang trọng và viền cyan sắc nét.
        Hỗ trợ 2 chế độ:
        - 'elapsed': '00:00:00.00 / 00:25:31' (Thời lượng video)
        - 'realtime': '2026-07-22 10:54:28.00' (Thời gian thực tế khi quay)
        """
        if frame is None or frame.size == 0:
            return frame

        if timeline_mode == "realtime":
            if start_datetime is None:
                start_dt_obj = datetime.datetime.now()
            elif isinstance(start_datetime, str):
                try:
                    start_dt_obj = datetime.datetime.fromisoformat(start_datetime.replace('/', '-'))
                except Exception:
                    start_dt_obj = datetime.datetime.now()
            else:
                start_dt_obj = start_datetime

            text = VideoProcessor.format_realtime(start_dt_obj, current_time_sec, show_millis=show_millis)
        else:
            cur_str = VideoProcessor.format_timecode(current_time_sec, show_millis=show_millis)
            if show_total and total_duration_sec > 0:
                tot_str = VideoProcessor.format_timecode(total_duration_sec, show_millis=False)
                text = f"{cur_str} / {tot_str}"
            else:
                text = cur_str

        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        pad = 12

        if position == "bottom_right":
            x2 = w - margin_x
            x1 = x2 - tw - 2 * pad
            y2 = h - margin_y
            y1 = y2 - th - 2 * pad
        elif position == "bottom_left":
            x1 = margin_x
            x2 = x1 + tw + 2 * pad
            y2 = h - margin_y
            y1 = y2 - th - 2 * pad
        elif position == "top_right":
            x2 = w - margin_x
            x1 = x2 - tw - 2 * pad
            y1 = margin_y
            y2 = y1 + th + 2 * pad
        else:  # top_left
            x1 = margin_x
            x2 = x1 + tw + 2 * pad
            y1 = margin_y
            y2 = y1 + th + 2 * pad

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        # 1. Vẽ nền đen bán trong suốt (Alpha = 0.70)
        sub_roi = frame[y1:y2, x1:x2]
        if sub_roi.size > 0:
            bg_box = np.full_like(sub_roi, (18, 18, 22), dtype=np.uint8)
            alpha = 0.70
            blended = cv2.addWeighted(bg_box, alpha, sub_roi, 1.0 - alpha, 0)
            frame[y1:y2, x1:x2] = blended

        # 2. Vẽ viền bo sắc nét (Màu Cyan #00d2ff -> BGR: (255, 210, 0))
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 210, 0), 2)

        # 3. Vẽ chữ thời gian màu trắng sáng
        text_x = x1 + pad
        text_y = y2 - pad
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        return frame

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
    def enhance_lighting_and_contrast(
        frame: np.ndarray,
        dark_boost: float = 50.0,
        clahe_amount: float = 40.0,
        sharpen_amount: float = 20.0,
        exclude_roi: Optional[Tuple[int, int, int, int]] = None,
        target_roi: Optional[Tuple[int, int, int, int]] = None,
        shadow_lift: float = 50.0,
        feather_radius: int = 20
    ) -> np.ndarray:
        """
        Tăng cường ánh sáng vùng tối cực mạnh bằng công thức Floor Lift Remapping:
          L_new = offset + (255 - offset) * (L / 255)^gamma
        Biến các vùng điểm ảnh tối om (L ~ 0..5) thành xám sáng rõ nét (L ~ 60..100).
        """
        if frame is None or frame.size == 0:
            return frame

        # Tối ưu hóa Fast-Path: Nếu không chỉnh tăng sáng/tương phản/nét, bỏ qua toàn bộ pipeline nặng
        if dark_boost < 0.5 and clahe_amount < 0.5 and sharpen_amount < 0.5 and shadow_lift < 0.5:
            return frame

        height, width = frame.shape[:2]

        # 1. Chuyển sang LAB color space để xử lý kênh độ sáng L độc lập
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        norm_l = l_channel.astype(np.float32) / 255.0

        # 2. Floor Lift Remapping Formula
        offset_val = (shadow_lift / 100.0) * 140.0
        gamma = 1.0 - (dark_boost / 100.0) * 0.80
        gamma = max(0.20, gamma)

        boosted_l = offset_val + (255.0 - offset_val) * np.power(norm_l, gamma)
        boosted_l = np.clip(boosted_l, 0, 255).astype(np.uint8)

        # 3. CLAHE Local Contrast Enhancement
        clip_limit = 1.0 + (clahe_amount / 12.0)  # 1.0 -> 9.3
        if clip_limit > 1.0:
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(boosted_l)
        else:
            l_enhanced = boosted_l

        # Trộn lại không gian màu LAB -> BGR
        enhanced_lab = cv2.merge((l_enhanced, a_channel, b_channel))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 4. Sharpening (Unsharp Masking)
        if sharpen_amount > 0:
            sigma = 1.5
            blurred = cv2.GaussianBlur(enhanced_bgr, (0, 0), sigma)
            strength = (sharpen_amount / 35.0)
            enhanced_bgr = cv2.addWeighted(enhanced_bgr, 1.0 + strength, blurred, -strength, 0)
            enhanced_bgr = np.clip(enhanced_bgr, 0, 255).astype(np.uint8)

        # 5. Xây dựng Alpha Mask trộn hình ảnh
        alpha_mask = np.zeros((height, width), dtype=np.float32)

        if target_roi is not None and target_roi[2] > 0 and target_roi[3] > 0:
            # Chế độ: CHỈ TÁC ĐỘNG VÙNG CHỈ ĐỊNH (Target ROI)
            tx, ty, tw, th = target_roi
            tx = max(0, min(tx, width - 1))
            ty = max(0, min(ty, height - 1))
            tw = max(1, min(tw, width - tx))
            th = max(1, min(th, height - ty))
            alpha_mask[ty:ty+th, tx:tx+tw] = 1.0
        else:
            # Chế độ: Tác động toàn bộ hình ảnh
            alpha_mask.fill(1.0)

        # Trừ đi vùng exclude_roi (Khung camera phụ)
        if exclude_roi is not None and exclude_roi[2] > 0 and exclude_roi[3] > 0:
            ex, ey, ew, eh = exclude_roi
            ex = max(0, min(ex, width - 1))
            ey = max(0, min(ey, height - 1))
            ew = max(1, min(ew, width - ex))
            eh = max(1, min(eh, height - ey))
            alpha_mask[ey:ey+eh, ex:ex+ew] = 0.0

        # Làm mượt biên bằng Gaussian Blur (Feathering)
        if feather_radius > 0:
            ksize = feather_radius * 2 + 1
            alpha_mask = cv2.GaussianBlur(alpha_mask, (ksize, ksize), 0)

        alpha_3ch = np.dstack([alpha_mask] * 3)
        out = (enhanced_bgr.astype(np.float32) * alpha_3ch + 
               frame.astype(np.float32) * (1.0 - alpha_3ch))
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def process_single_frame(
        frame: np.ndarray,
        mode: str,
        roi: Tuple[int, int, int, int],
        tracker: Optional[Any] = None,
        padding: int = 10,
        dark_boost: float = 50.0,
        clahe_amount: float = 40.0,
        sharpen_amount: float = 20.0,
        shadow_lift: float = 40.0,
        target_roi: Optional[Tuple[int, int, int, int]] = None,
        exclude_roi: Optional[Tuple[int, int, int, int]] = None,
        feather_radius: int = 20,
        show_timeline: bool = False,
        timeline_mode: str = "elapsed",
        start_datetime: Optional[Union[datetime.datetime, str]] = None,
        current_time_sec: float = 0.0,
        total_duration_sec: float = 0.0,
        timeline_position: str = "bottom_right"
    ) -> np.ndarray:
        """
        Xử lý 1 khung hình đơn lẻ dựa theo chế độ mode và tọa độ ROI / Tracker.
        Hỗ trợ gắn thêm OSD Timeline vào góc video nếu show_timeline=True.
        """
        height, width = frame.shape[:2]

        if mode == ProcessingMode.ENHANCE_LIGHT:
            out_frame = VideoProcessor.enhance_lighting_and_contrast(
                frame=frame,
                dark_boost=dark_boost,
                clahe_amount=clahe_amount,
                sharpen_amount=sharpen_amount,
                shadow_lift=shadow_lift,
                target_roi=target_roi,
                exclude_roi=exclude_roi,
                feather_radius=feather_radius
            )
        elif mode == ProcessingMode.CROP:
            crop_w = roi[0] if roi else int(width * 0.8)
            crop_w = max(1, min(crop_w, width))
            out_frame = frame[0:height, 0:crop_w].copy()
        elif mode == ProcessingMode.NONE:
            out_frame = frame.copy()
        else:
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

        # Gắn OSD Timeline nếu được kích hoạt
        if show_timeline:
            out_frame = VideoProcessor.draw_timeline_overlay(
                frame=out_frame,
                current_time_sec=current_time_sec,
                total_duration_sec=total_duration_sec,
                timeline_mode=timeline_mode,
                start_datetime=start_datetime,
                position=timeline_position
            )

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
        dark_boost: float = 50.0,
        clahe_amount: float = 40.0,
        sharpen_amount: float = 20.0,
        shadow_lift: float = 40.0,
        target_roi: Optional[Tuple[int, int, int, int]] = None,
        exclude_roi: Optional[Tuple[int, int, int, int]] = None,
        feather_radius: int = 20,
        show_timeline: bool = True,
        timeline_mode: str = "elapsed",
        start_datetime: Optional[Union[datetime.datetime, str]] = None,
        timeline_position: str = "bottom_right",
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        stop_checker: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Vòng lặp chính xử lý video xuất ra file kết quả. Hỗ trợ cắt/chọn khoảng thời gian (start_time -> end_time)
        và chèn OSD Timeline (elapsed hoặc realtime).
        Tự động lưu vào thư mục outputs/ nếu output_path không được truyền vào.
        """
        info = cls.get_video_info(video_path)
        width = info["width"]
        height = info["height"]
        fps = info["fps"]
        total_frames = info["total_frames"]
        total_duration_sec = info["duration_sec"]

        if timeline_mode == "realtime" and start_datetime is None:
            start_datetime = cls.get_video_start_datetime(video_path, total_duration_sec)

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
        if mode not in (ProcessingMode.CROP, ProcessingMode.ENHANCE_LIGHT, ProcessingMode.NONE) and roi is not None:
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

                current_time_sec = current_frame_pos / fps if fps > 0 else 0.0
                current_frame_pos += 1
                processed_count += 1

                out_frame = cls.process_single_frame(
                    frame=frame,
                    mode=mode,
                    roi=roi if roi else (0, 0, width, height),
                    tracker=tracker,
                    padding=padding,
                    dark_boost=dark_boost,
                    clahe_amount=clahe_amount,
                    sharpen_amount=sharpen_amount,
                    shadow_lift=shadow_lift,
                    target_roi=target_roi,
                    exclude_roi=exclude_roi,
                    feather_radius=feather_radius,
                    show_timeline=show_timeline,
                    timeline_mode=timeline_mode,
                    start_datetime=start_datetime,
                    current_time_sec=current_time_sec,
                    total_duration_sec=total_duration_sec,
                    timeline_position=timeline_position
                )
                writer.write(out_frame)

                if progress_callback:
                    pct = (processed_count / target_frames) * 100.0
                    progress_callback(pct, processed_count, target_frames)

        finally:
            cap.release()
            writer.release()

        return output_path

    @staticmethod
    def resize_with_letterbox(
        frame: np.ndarray,
        target_width: int,
        target_height: int,
        maintain_aspect_ratio: bool = True
    ) -> np.ndarray:
        """
        Resize khung hình về kích thước đích (target_width x target_height).
        Nếu maintain_aspect_ratio=True, thêm viền đen (Letterbox) để giữ nguyên tỷ lệ, chống méo hình.
        """
        if frame is None or frame.size == 0:
            return frame
        h, w = frame.shape[:2]
        if w == target_width and h == target_height:
            return frame

        if not maintain_aspect_ratio:
            return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

        # Tính toán scale giữ tỷ lệ
        scale = min(target_width / w, target_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # Căn giữa hình ảnh trên canvas đen
        x_offset = (target_width - new_w) // 2
        y_offset = (target_height - new_h) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
        return canvas

    @classmethod
    def concatenate_videos(
        cls,
        video_paths: List[str],
        output_path: Optional[str] = None,
        target_resolution: Optional[Tuple[int, int]] = None,
        target_fps: Optional[float] = None,
        maintain_aspect_ratio: bool = True,
        show_timeline: bool = False,
        timeline_mode: str = "elapsed",
        timeline_position: str = "bottom_right",
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        stop_checker: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Ghép danh sách nhiều video thành 1 video duy nhất.
        - Tự động chuẩn hóa độ phân giải & FPS nếu các clip không đồng nhất.
        - Hỗ trợ thêm viền đen Letterbox chống méo hình nếu tỉ lệ khung hình khác nhau.
        - Hỗ trợ gắn OSD Timeline (elapsed: tổng thời lượng tăng dần liên tục, hoặc realtime theo từng clip).
        - Hỗ trợ progress_callback (% trên tổng toàn bộ frame) và stop_checker (dừng an toàn).
        """
        if not video_paths:
            raise ValueError("Danh sách video đầu vào không được để trống!")

        valid_paths = [p for p in video_paths if os.path.exists(p)]
        if not valid_paths:
            raise FileNotFoundError("Không tìm thấy file video hợp lệ nào trong danh sách đầu vào!")

        # 1. Thu thập metadata của tất cả video
        videos_info = []
        total_all_frames = 0
        total_duration_all = 0.0

        for path in valid_paths:
            info = cls.get_video_info(path)
            videos_info.append(info)
            total_all_frames += info["total_frames"]
            total_duration_all += info["duration_sec"]

        if total_all_frames <= 0:
            raise ValueError("Tổng số frames của các video bằng 0, không thể xử lý!")

        # 2. Xác định độ phân giải và FPS chuẩn cho video đầu ra
        first_info = videos_info[0]
        if target_resolution is not None and target_resolution[0] > 0 and target_resolution[1] > 0:
            out_w, out_h = target_resolution
        else:
            out_w, out_h = first_info["width"], first_info["height"]

        fps = target_fps if (target_fps is not None and target_fps > 0) else (first_info["fps"] if first_info["fps"] > 0 else 30.0)

        # 3. Chuẩn bị file output
        if output_path is None:
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"merged_video_{timestamp_str}.mp4")
        else:
            out_parent = os.path.dirname(os.path.abspath(output_path))
            if out_parent:
                os.makedirs(out_parent, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
        if not writer.isOpened():
            raise IOError(f"Không thể khởi tạo VideoWriter cho file '{output_path}'")

        processed_total_frames = 0
        cumulative_elapsed_sec = 0.0

        try:
            for vid_idx, (path, info) in enumerate(zip(valid_paths, videos_info)):
                if stop_checker and stop_checker():
                    break

                cap = cv2.VideoCapture(path)
                if not cap.isOpened():
                    continue

                vid_fps = info["fps"] if info["fps"] > 0 else fps
                vid_frames = info["total_frames"]
                vid_duration = info["duration_sec"]
                vid_start_dt = cls.get_video_start_datetime(path, vid_duration) if timeline_mode == "realtime" else None

                frame_idx_in_video = 0
                while cap.isOpened():
                    if stop_checker and stop_checker():
                        break

                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    # Chuẩn hóa kích thước frame
                    norm_frame = cls.resize_with_letterbox(
                        frame=frame,
                        target_width=out_w,
                        target_height=out_h,
                        maintain_aspect_ratio=maintain_aspect_ratio
                    )

                    # Gắn OSD Timeline nếu được yêu cầu
                    if show_timeline:
                        current_vid_sec = frame_idx_in_video / vid_fps if vid_fps > 0 else 0.0
                        if timeline_mode == "realtime":
                            # Realtime OSD dựa theo thời gian thực của clip hiện tại
                            norm_frame = cls.draw_timeline_overlay(
                                frame=norm_frame,
                                current_time_sec=current_vid_sec,
                                total_duration_sec=vid_duration,
                                timeline_mode="realtime",
                                start_datetime=vid_start_dt,
                                position=timeline_position
                            )
                        else:
                            # Elapsed OSD tăng dần liên tục theo tổng thời lượng video ghép
                            total_curr_sec = cumulative_elapsed_sec + current_vid_sec
                            norm_frame = cls.draw_timeline_overlay(
                                frame=norm_frame,
                                current_time_sec=total_curr_sec,
                                total_duration_sec=total_duration_all,
                                timeline_mode="elapsed",
                                position=timeline_position
                            )

                    writer.write(norm_frame)

                    frame_idx_in_video += 1
                    processed_total_frames += 1

                    if progress_callback:
                        pct = min(100.0, (processed_total_frames / total_all_frames) * 100.0)
                        progress_callback(pct, processed_total_frames, total_all_frames)

                cap.release()
                cumulative_elapsed_sec += vid_duration

        finally:
            writer.release()

        return output_path
