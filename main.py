"""
Entry Point khởi chạy chính cho ứng dụng Xóa & Che Đối Tượng Video.

Cách dùng:
  - Khởi chạy Giao diện đồ họa (GUI): python main.py
  - Khởi chạy Dòng lệnh (CLI):        python main.py --cli --input <file.mp4> [options]
"""

import sys
import os

# Thêm thư mục gốc và src vào Python Path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def main():
    if "--cli" in sys.argv:
        # Bỏ cờ --cli để argparse trong CLI không bị lỗi
        sys.argv.remove("--cli")
        from src.cli.video_object_remover import run_cli
        run_cli(sys.argv[1:])
    else:
        import tkinter as tk
        from src.gui.app_gui import VideoObjectRemoverApp
        
        root = tk.Tk()
        app = VideoObjectRemoverApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()
