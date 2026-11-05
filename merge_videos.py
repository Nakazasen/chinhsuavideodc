#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ dòng lệnh ghép nối nhiều video thành 1 video duy nhất (Video Merger / Concatenator).
Sử dụng lớp Model VideoProcessor từ package src.core.
"""

import os
import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.video_processor import VideoProcessor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description="Ghép nối nhiều video thành 1 video duy nhất với tính năng tự động chuẩn hóa kích thước và gắn Timeline OSD."
    )
    parser.add_argument(
        "--inputs", "-i",
        nargs="+",
        required=True,
        help="Danh sách đường dẫn các file video đầu vào cần ghép (theo thứ tự)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Đường dẫn file video đầu ra (mặc định: outputs/merged_video_<timestamp>.mp4)"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=None,
        help="Chiều rộng khung hình đầu ra (pixel, ví dụ: 1920). Mặc định lấy theo video đầu tiên."
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=None,
        help="Chiều cao khung hình đầu ra (pixel, ví dụ: 1080). Mặc định lấy theo video đầu tiên."
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Tốc độ khung hình đầu ra (FPS, ví dụ: 30.0). Mặc định lấy theo video đầu tiên."
    )
    parser.add_argument(
        "--no-letterbox",
        action="store_true",
        help="Không thêm viền đen (kéo giãn hình ảnh trực tiếp thay vì giữ tỷ lệ)"
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        default=False,
        help="Gắn Timeline / Timecode OSD vào góc video ghép"
    )
    parser.add_argument(
        "--timeline-mode",
        default="elapsed",
        choices=["elapsed", "realtime"],
        help="Chế độ timeline: 'elapsed' (thời lượng tổng cộng liên tục) hoặc 'realtime' (theo giờ quay thực tế mỗi clip)"
    )
    parser.add_argument(
        "--position",
        default="bottom_right",
        choices=["bottom_right", "bottom_left", "top_right", "top_left"],
        help="Vị trí gắn OSD Timeline (mặc định: bottom_right)"
    )

    args = parser.parse_args()

    input_paths = [os.path.abspath(p) for p in args.inputs]
    valid_paths = []
    for p in input_paths:
        if not os.path.exists(p):
            print(f"[!] Cảnh báo: Không tìm thấy file '{p}', sẽ bỏ qua.")
        else:
            valid_paths.append(p)

    if not valid_paths:
        print("[!] Lỗi: Không có file video hợp lệ nào để ghép!")
        sys.exit(1)

    print("=" * 65)
    print("🎬 CÔNG CỤ GHÉP NỐI NHIỀU VIDEO (VIDEO MERGER)")
    print("=" * 65)
    print(f"Tổng số video đầu vào hợp lệ: {len(valid_paths)}")

    total_frames = 0
    total_duration = 0.0
    for idx, p in enumerate(valid_paths, 1):
        info = VideoProcessor.get_video_info(p)
        total_frames += info["total_frames"]
        total_duration += info["duration_sec"]
        tc_str = VideoProcessor.format_timecode(info["duration_sec"], show_millis=False)
        print(f"  [{idx}] {os.path.basename(p)} | {info['width']}x{info['height']} @ {info['fps']:.1f}fps | {tc_str} ({info['total_frames']} frames)")

    total_tc_str = VideoProcessor.format_timecode(total_duration, show_millis=False)
    print(f"👉 Tổng thời lượng ghép: {total_tc_str} ({total_frames} frames)")
    
    target_res = (args.width, args.height) if (args.width and args.height) else None
    if target_res:
        print(f"Độ phân giải đầu ra tùy chỉnh: {target_res[0]}x{target_res[1]}")
    if args.fps:
        print(f"FPS đầu ra tùy chỉnh: {args.fps:.2f}")
    print(f"Giữ tỷ lệ (Letterbox): {'KHÔNG' if args.no_letterbox else 'CÓ'}")
    print(f"Gắn Timeline OSD: {'BẬT (' + args.timeline_mode + ')' if args.timeline else 'TẮT'}")
    print("=" * 65)

    def progress_callback(pct: float, current: int, total: int):
        if current % 60 == 0 or current == total:
            sys.stdout.write(f"\r⏳ Tiến độ ghép: {current}/{total} frames ({pct:.1f}%)")
            sys.stdout.flush()

    try:
        out_file = VideoProcessor.concatenate_videos(
            video_paths=valid_paths,
            output_path=args.output,
            target_resolution=target_res,
            target_fps=args.fps,
            maintain_aspect_ratio=not args.no_letterbox,
            show_timeline=args.timeline,
            timeline_mode=args.timeline_mode,
            timeline_position=args.position,
            progress_callback=progress_callback
        )
        print(f"\n\n✅ GHÉP VIDEO THÀNH CÔNG! File đã được lưu tại:\n👉 {out_file}")
    except KeyboardInterrupt:
        print("\n[!] Đã dừng theo yêu cầu của người dùng.")
    except Exception as e:
        print(f"\n[!] Lỗi trong quá trình ghép video: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
