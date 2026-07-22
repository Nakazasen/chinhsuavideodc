"""
Công cụ dòng lệnh (CLI) xóa / che đối tượng trong video.
Tái sử dụng lớp Model VideoProcessor từ package src.core.
"""

import os
import sys
import argparse
import cv2

# Xử lý đường dẫn import khi chạy từ root hoặc trực tiếp từ file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.core.video_processor import VideoProcessor, ProcessingMode

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def select_roi_interactively(video_path: str):
    """Mở cửa sổ GUI OpenCV cho phép người dùng vẽ chọn vùng ROI bằng chuột."""
    cap = cv2.VideoCapture(video_path)
    ret, first_frame = cap.read()
    cap.release()

    if not ret or first_frame is None:
        print("Lỗi: Không thể đọc frame đầu tiên của video!")
        return None

    height, width = first_frame.shape[:2]
    disp_scale = 1.0
    max_disp_h = 800
    if height > max_disp_h:
        disp_scale = max_disp_h / height
        disp_w = int(width * disp_scale)
        disp_h = int(height * disp_scale)
        disp_frame = cv2.resize(first_frame, (disp_w, disp_h))
    else:
        disp_frame = first_frame.copy()

    win_name = "KHOANH VUNG DOI TUONG (Nhan ENTER de chon, ESC/q de thoat)"
    print("\n[HƯỚNG DẪN KHOANH VÙNG]")
    print("1. Dùng chuột kéo chọn đối tượng cần xóa trên cửa sổ.")
    print("2. Nhấn ENTER hoặc SPACE để xác nhận chọn.")
    print("3. Nhấn ESC hoặc phím 'q' để HỦY / THOÁT CHƯƠNG TRÌNH.\n")

    cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)
    selected_roi = cv2.selectROI(win_name, disp_frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    if selected_roi[2] == 0 or selected_roi[3] == 0:
        print(">> Đã hủy hoặc không chọn vùng nào. Đang thoát!")
        return None

    x = int(selected_roi[0] / disp_scale)
    y = int(selected_roi[1] / disp_scale)
    w = int(selected_roi[2] / disp_scale)
    h = int(selected_roi[3] / disp_scale)

    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = min(w, width - x)
    h = min(h, height - y)

    return (x, y, w, h)


def progress_reporter(pct: float, current: int, total: int):
    """Callback in tiến độ xử lý ra terminal."""
    print(f"Tiến độ: {current}/{total} frames ({pct:.1f}%)")


def run_cli(args=None):
    parser = argparse.ArgumentParser(
        description="Chương trình xóa/che đối tượng trong video bằng Object Tracking & Inpainting."
    )
    parser.add_argument('--input', type=str, help='Đường dẫn file video đầu vào')
    parser.add_argument(
        '--mode',
        type=str,
        default=ProcessingMode.INPAINT,
        choices=ProcessingMode.ALL_MODES,
        help='Chế độ xử lý: inpaint, mask, blur, crop'
    )
    parser.add_argument(
        '--roi',
        type=int,
        nargs=4,
        metavar=('X', 'Y', 'W', 'H'),
        help='Tọa độ ROI cố định: x y w h'
    )
    parser.add_argument(
        '--padding',
        type=int,
        default=10,
        help='Khoảng bù lề pixel mở rộng ROI (default: 10)'
    )
    parser.add_argument(
        '--start-time',
        type=float,
        default=0.0,
        help='Thời gian bắt đầu xử lý tính bằng giây (default: 0.0)'
    )
    parser.add_argument(
        '--end-time',
        type=float,
        default=None,
        help='Thời gian kết thúc xử lý tính bằng giây (default: tới hết video)'
    )

    parsed_args = parser.parse_args(args)

    video_path = parsed_args.input
    if not video_path:
        search_dirs = ['.', 'samples']
        found_videos = []
        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                found_videos.extend([
                    os.path.join(s_dir, f) for f in os.listdir(s_dir)
                    if f.endswith('.mp4') and not f.endswith('_processed.mp4')
                    and not f.endswith('_cropped.mp4') and not f.endswith('_masked.mp4')
                ])

        if found_videos:
            video_path = found_videos[0]
            print(f"Phát hiện video tự động: {video_path}")
        else:
            print("Cách dùng: python main.py --cli --input <file_video.mp4>")
            sys.exit(1)

    try:
        info = VideoProcessor.get_video_info(video_path)
        print("--- THÔNG TIN VIDEO ---")
        print(f"File: {info['path']}")
        print(f"Độ phân giải: {info['width']}x{info['height']} | FPS: {info['fps']:.2f} | Tổng frame: {info['total_frames']}")
    except Exception as e:
        print(f"Lỗi: {e}")
        sys.exit(1)

    roi = tuple(parsed_args.roi) if parsed_args.roi else None
    if roi is None and parsed_args.mode != ProcessingMode.CROP:
        roi = select_roi_interactively(video_path)
        if roi is None:
            sys.exit(0)

    print(f"\n[BẮT ĐẦU XỬ LÝ VIDEO - Chế độ: {parsed_args.mode.upper()}]")
    if roi:
        print(f"Vùng ROI chọn: x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}")

    try:
        output_file = VideoProcessor.process_video(
            video_path=video_path,
            mode=parsed_args.mode,
            roi=roi,
            padding=parsed_args.padding,
            start_time=parsed_args.start_time,
            end_time=parsed_args.end_time,
            progress_callback=progress_reporter
        )
        print(f"\nTHÀNH CÔNG! File kết quả đã lưu tại: {output_file}")
    except KeyboardInterrupt:
        print("\n>> Người dùng đã dừng chương trình bằng bàn phím (Ctrl+C).")
    except Exception as err:
        print(f"\nXảy ra lỗi trong quá trình xử lý: {err}")


if __name__ == '__main__':
    run_cli()
