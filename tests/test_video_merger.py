"""
Unit & Integration Test Suite cho tính năng Ghép Video (Video Concatenator / Merger).
"""

import os
import sys
import tempfile
import numpy as np
import cv2
import pytest

# Thiết lập đường dẫn import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.core.video_processor import VideoProcessor, ProcessingMode


def _create_dummy_video(
    filepath: str,
    width: int = 320,
    height: int = 240,
    fps: float = 30.0,
    num_frames: int = 15,
    color_bgr: tuple = (0, 0, 255)
):
    """Tạo file video giả lập để kiểm thử tự động."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    for i in range(num_frames):
        frame = np.full((height, width, 3), color_bgr, dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (20, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()


class TestVideoProcessorLetterbox:
    """Kiểm thử thuật toán Letterbox Resize."""

    def test_resize_same_dimensions(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        out = VideoProcessor.resize_with_letterbox(frame, target_width=640, target_height=480)
        assert out.shape == (480, 640, 3)

    def test_resize_letterbox_padding(self):
        # 4:3 input (640x480) vào 16:9 target (1280x720) -> Phải có viền đen 2 bên
        frame = np.full((480, 640, 3), (100, 150, 200), dtype=np.uint8)
        out = VideoProcessor.resize_with_letterbox(frame, target_width=1280, target_height=720, maintain_aspect_ratio=True)
        assert out.shape == (720, 1280, 3)
        # Điểm ảnh ở góc mép trái ngoài cùng phải là màu đen (0, 0, 0)
        assert np.array_equal(out[360, 10], [0, 0, 0])

    def test_resize_no_letterbox_direct_stretch(self):
        frame = np.full((480, 640, 3), (100, 150, 200), dtype=np.uint8)
        out = VideoProcessor.resize_with_letterbox(frame, target_width=1280, target_height=720, maintain_aspect_ratio=False)
        assert out.shape == (720, 1280, 3)
        # Toàn bộ ảnh được kéo giãn, góc không phải màu đen
        assert np.array_equal(out[360, 10], [100, 150, 200])


class TestVideoProcessorConcatenation:
    """Kiểm thử tính năng ghép video."""

    def test_concatenate_two_videos_same_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "v1.mp4")
            v2 = os.path.join(tmpdir, "v2.mp4")
            out_v = os.path.join(tmpdir, "merged.mp4")

            _create_dummy_video(v1, width=320, height=240, fps=30.0, num_frames=15, color_bgr=(255, 0, 0))
            _create_dummy_video(v2, width=320, height=240, fps=30.0, num_frames=25, color_bgr=(0, 255, 0))

            progress_calls = []

            def on_progress(pct, current, total):
                progress_calls.append((pct, current, total))

            result = VideoProcessor.concatenate_videos(
                video_paths=[v1, v2],
                output_path=out_v,
                progress_callback=on_progress
            )

            assert os.path.exists(result)
            info = VideoProcessor.get_video_info(result)
            assert info["width"] == 320
            assert info["height"] == 240
            assert info["total_frames"] == 40  # 15 + 25
            assert len(progress_calls) > 0
            assert progress_calls[-1][0] == 100.0

    def test_concatenate_videos_different_resolutions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "v1_small.mp4")
            v2 = os.path.join(tmpdir, "v2_large.mp4")
            out_v = os.path.join(tmpdir, "merged_diff_res.mp4")

            _create_dummy_video(v1, width=320, height=240, fps=30.0, num_frames=10)
            _create_dummy_video(v2, width=640, height=480, fps=30.0, num_frames=10)

            # Ghép với target_resolution = 640x480
            result = VideoProcessor.concatenate_videos(
                video_paths=[v1, v2],
                output_path=out_v,
                target_resolution=(640, 480),
                maintain_aspect_ratio=True
            )

            assert os.path.exists(result)
            info = VideoProcessor.get_video_info(result)
            assert info["width"] == 640
            assert info["height"] == 480
            assert info["total_frames"] == 20

    def test_concatenate_with_timeline_overlay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "v1.mp4")
            v2 = os.path.join(tmpdir, "v2.mp4")
            out_v = os.path.join(tmpdir, "merged_timeline.mp4")

            _create_dummy_video(v1, width=320, height=240, fps=30.0, num_frames=15)
            _create_dummy_video(v2, width=320, height=240, fps=30.0, num_frames=15)

            result = VideoProcessor.concatenate_videos(
                video_paths=[v1, v2],
                output_path=out_v,
                show_timeline=True,
                timeline_mode="elapsed"
            )

            assert os.path.exists(result)
            info = VideoProcessor.get_video_info(result)
            assert info["total_frames"] == 30

    def test_concatenate_stop_early(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "v1.mp4")
            v2 = os.path.join(tmpdir, "v2.mp4")
            out_v = os.path.join(tmpdir, "merged_stopped.mp4")

            _create_dummy_video(v1, width=320, height=240, fps=30.0, num_frames=30)
            _create_dummy_video(v2, width=320, height=240, fps=30.0, num_frames=30)

            # Dừng ngay khi đạt frame 10
            frame_counter = [0]

            def stop_check():
                frame_counter[0] += 1
                return frame_counter[0] >= 10

            result = VideoProcessor.concatenate_videos(
                video_paths=[v1, v2],
                output_path=out_v,
                stop_checker=stop_check
            )

            assert os.path.exists(result)
            info = VideoProcessor.get_video_info(result)
            assert info["total_frames"] < 60

    def test_concatenate_empty_inputs(self):
        with pytest.raises(ValueError):
            VideoProcessor.concatenate_videos(video_paths=[])

    def test_concatenate_nonexistent_files(self):
        with pytest.raises(FileNotFoundError):
            VideoProcessor.concatenate_videos(video_paths=["nonexistent_file_1.mp4", "nonexistent_file_2.mp4"])
