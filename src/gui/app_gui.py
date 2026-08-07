"""
Giao diện người dùng Tkinter (View/Presenter) cho ứng dụng xóa & che đối tượng video.
Tái sử dụng lớp Model VideoProcessor từ package src.core.
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageTk

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


class VideoObjectRemoverApp:
    """Lớp quản lý giao diện ứng dụng (View) và điều khiển sự kiện (Presenter)."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Công Cụ Xóa / Che Đối Tượng Video - AI Studio")
        self.root.geometry("1240x840")
        self.root.minsize(950, 600)

        # Trạng thái ứng dụng (State)
        self.video_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.orig_w = 0
        self.orig_h = 0

        self.current_frame_idx = 0
        self.current_frame_img = None
        self.display_image = None
        self.disp_scale_w = 1.0
        self.disp_scale_h = 1.0

        # Tọa độ ROI (x, y, w, h)
        self.roi = None
        self.start_x = None
        self.start_y = None
        self.offset_x = 0
        self.offset_y = 0

        self.is_processing = False
        self.stop_requested = False
        self.is_playing_preview = False
        self.preview_timer_id = None

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        self.bg_dark = "#1e1e2e"
        self.bg_card = "#2b2b3b"
        self.accent_color = "#007acc"
        self.accent_hover = "#005999"
        self.text_color = "#ffffff"
        self.sub_text = "#a0a0b0"

        self.root.configure(bg=self.bg_dark)

        style.configure("TFrame", background=self.bg_dark)
        style.configure("Card.TFrame", background=self.bg_card, relief="flat")
        style.configure("TLabel", background=self.bg_dark, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=self.bg_card, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.bg_dark, foreground=self.text_color, font=("Segoe UI", 14, "bold"))
        style.configure("Header.TLabel", background=self.bg_card, foreground="#00d2ff", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background=self.bg_card, foreground="#00ffaa", font=("Segoe UI", 10, "bold"))

        style.configure("Accent.TButton", background=self.accent_color, foreground="white", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("Accent.TButton", background=[("active", self.accent_hover)])

        style.configure("Stop.TButton", background="#d9534f", foreground="white", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("Stop.TButton", background=[("active", "#c9302c")])

    def _build_ui(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=15, pady=8)

        lbl_title = ttk.Label(
            header_frame,
            text="CHƯƠNG TRÌNH XÓA & CHE ĐỐI TƯỢNG VIDEO (Standard Package Structure)",
            style="Title.TLabel"
        )
        lbl_title.pack(side="left")

        main_paned = ttk.Frame(self.root)
        main_paned.pack(fill="both", expand=True, padx=15, pady=5)

        # Thêm cuộn Scrollbar cho cột bảng điều khiển bên trái
        left_container = ttk.Frame(main_paned, style="Card.TFrame", width=380)
        left_container.pack(side="left", fill="both", padx=(0, 10), pady=5)
        left_container.pack_propagate(False)

        left_canvas = tk.Canvas(left_container, bg=self.bg_card, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)

        left_frame = ttk.Frame(left_canvas, style="Card.TFrame")
        left_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )

        canvas_window = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_left_canvas_resize(event):
            left_canvas.itemconfig(canvas_window, width=event.width)

        left_canvas.bind("<Configure>", _on_left_canvas_resize)

        scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            if left_canvas.winfo_exists():
                left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        right_frame = ttk.Frame(main_paned, style="Card.TFrame")
        right_frame.pack(side="right", fill="both", expand=True, pady=5)

        # --- LEFT PANEL CONTROLS ---
        sec1 = ttk.Frame(left_frame, style="Card.TFrame")
        sec1.pack(fill="x", padx=12, pady=5)

        ttk.Label(sec1, text="1. Chọn Video Đầu Vào", style="Header.TLabel").pack(anchor="w", pady=(0, 3))
        btn_open = ttk.Button(sec1, text="Mở File Video...", style="Accent.TButton", command=self._browse_video)
        btn_open.pack(fill="x", pady=3)

        self.lbl_filename = ttk.Label(sec1, text="Chưa chọn video nào", style="Card.TLabel", wraplength=330)
        self.lbl_filename.pack(anchor="w", pady=2)

        self.lbl_info = ttk.Label(sec1, text="", style="Card.TLabel", foreground=self.sub_text)
        self.lbl_info.pack(anchor="w")

        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # Section 2: Mode & Settings
        sec2 = ttk.Frame(left_frame, style="Card.TFrame")
        sec2.pack(fill="x", padx=12, pady=5)

        ttk.Label(sec2, text="2. Chế Độ Xử Lý & Cấu Hình", style="Header.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(sec2, text="Chế độ:", style="Card.TLabel").pack(anchor="w", pady=(3, 1))

        self.combo_mode = ttk.Combobox(sec2, state="readonly", values=[
            "Inpaint - Xóa đối tượng & tái tạo nền",
            "Masking - Phủ khối màu che đối tượng",
            "Blur - Làm mờ mạnh (Gaussian Blur)",
            "Crop - Cắt viền lề không chứa đối tượng",
            "Enhance Light - Tăng sáng vùng tối & nét"
        ])
        self.combo_mode.current(4)  # Mặc định chọn chế độ Enhance Light
        self.combo_mode.pack(fill="x", pady=2)
        self.combo_mode.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Enhance Light Settings Panel (Mặc định hiển thị)
        self.enhance_frame = ttk.Frame(sec2, style="Card.TFrame")

        ttk.Label(self.enhance_frame, text="📍 Phạm vi làm sáng:", style="Header.TLabel", foreground="#00d2ff").pack(anchor="w", pady=(4, 2))
        
        self.var_enhance_scope = tk.StringVar(value="target_roi")
        r1 = ttk.Radiobutton(
            self.enhance_frame,
            text="🎯 Chỉ làm sáng VÙNG ĐƯỢC CHỌN (Kéo khoanh ô)",
            value="target_roi",
            variable=self.var_enhance_scope,
            command=self._redraw_canvas
        )
        r1.pack(anchor="w", pady=1)

        r2 = ttk.Radiobutton(
            self.enhance_frame,
            text="🌐 Làm sáng TOÀN BỘ (Loại trừ Camera phụ)",
            value="all",
            variable=self.var_enhance_scope,
            command=self._redraw_canvas
        )
        r2.pack(anchor="w", pady=1)

        # 1. Shadow Lift
        f_lift = ttk.Frame(self.enhance_frame, style="Card.TFrame")
        f_lift.pack(fill="x", pady=(4, 1))
        ttk.Label(f_lift, text="💡 Kích sáng nền đen (Shadow Lift):", style="Card.TLabel").pack(side="left")
        self.lbl_val_shadow_lift = ttk.Label(f_lift, text="50", style="Card.TLabel", foreground="#00ffaa", font=("Segoe UI", 10, "bold"))
        self.lbl_val_shadow_lift.pack(side="right")

        self.scale_shadow_lift = ttk.Scale(self.enhance_frame, from_=0, to=100, orient="horizontal", command=self._on_shadow_lift_change)
        self.scale_shadow_lift.set(50)
        self.scale_shadow_lift.pack(fill="x", pady=1)

        # 2. Dark Boost
        f_dark = ttk.Frame(self.enhance_frame, style="Card.TFrame")
        f_dark.pack(fill="x", pady=(4, 1))
        ttk.Label(f_dark, text="☀️ Tăng sáng vùng tối (Dark Boost):", style="Card.TLabel").pack(side="left")
        self.lbl_val_dark_boost = ttk.Label(f_dark, text="50", style="Card.TLabel", foreground="#00ffaa", font=("Segoe UI", 10, "bold"))
        self.lbl_val_dark_boost.pack(side="right")

        self.scale_dark_boost = ttk.Scale(self.enhance_frame, from_=0, to=100, orient="horizontal", command=self._on_dark_boost_change)
        self.scale_dark_boost.set(50)
        self.scale_dark_boost.pack(fill="x", pady=1)

        # 3. CLAHE
        f_clahe = ttk.Frame(self.enhance_frame, style="Card.TFrame")
        f_clahe.pack(fill="x", pady=(4, 1))
        ttk.Label(f_clahe, text="🔍 Độ tương phản (CLAHE):", style="Card.TLabel").pack(side="left")
        self.lbl_val_clahe = ttk.Label(f_clahe, text="40", style="Card.TLabel", foreground="#00ffaa", font=("Segoe UI", 10, "bold"))
        self.lbl_val_clahe.pack(side="right")

        self.scale_clahe = ttk.Scale(self.enhance_frame, from_=0, to=100, orient="horizontal", command=self._on_clahe_change)
        self.scale_clahe.set(40)
        self.scale_clahe.pack(fill="x", pady=1)

        # 4. Sharpen
        f_sharpen = ttk.Frame(self.enhance_frame, style="Card.TFrame")
        f_sharpen.pack(fill="x", pady=(4, 1))
        ttk.Label(f_sharpen, text="✨ Độ sắc nét (Sharpen):", style="Card.TLabel").pack(side="left")
        self.lbl_val_sharpen = ttk.Label(f_sharpen, text="20", style="Card.TLabel", foreground="#00ffaa", font=("Segoe UI", 10, "bold"))
        self.lbl_val_sharpen.pack(side="right")

        self.scale_sharpen = ttk.Scale(self.enhance_frame, from_=0, to=100, orient="horizontal", command=self._on_sharpen_change)
        self.scale_sharpen.set(20)
        self.scale_sharpen.pack(fill="x", pady=1)

        self.var_auto_protect_pip = tk.BooleanVar(value=True)
        self.chk_auto_pip = ttk.Checkbutton(
            self.enhance_frame,
            text="🔒 Mặc định khóa góc phải (Camera phụ 2)",
            variable=self.var_auto_protect_pip,
            command=self._redraw_canvas
        )
        self.chk_auto_pip.pack(anchor="w", pady=4)

        ttk.Label(sec2, text="Padding mở rộng ROI (pixel):", style="Card.TLabel").pack(anchor="w", pady=(5, 1))
        self.spin_padding = ttk.Spinbox(sec2, from_=0, to=50, increment=2)
        self.spin_padding.set(10)
        self.spin_padding.pack(fill="x", pady=2)

        ttk.Label(sec2, text="Cắt video (Khoảng giây xử lý test):", style="Card.TLabel").pack(anchor="w", pady=(5, 1))
        time_frame = ttk.Frame(sec2, style="Card.TFrame")
        time_frame.pack(fill="x", pady=2)

        ttk.Label(time_frame, text="Từ (s):", style="Card.TLabel").pack(side="left")
        self.entry_start_time = ttk.Entry(time_frame, width=6)
        self.entry_start_time.insert(0, "0.0")
        self.entry_start_time.pack(side="left", padx=(4, 12))

        ttk.Label(time_frame, text="Đến (s):", style="Card.TLabel").pack(side="left")
        self.entry_end_time = ttk.Entry(time_frame, width=6)
        self.entry_end_time.pack(side="left", padx=(4, 0))

        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # Section 3: Selected ROI Info
        sec3 = ttk.Frame(left_frame, style="Card.TFrame")
        sec3.pack(fill="x", padx=12, pady=5)

        ttk.Label(sec3, text="3. Tọa Độ Đối Tượng (ROI)", style="Header.TLabel").pack(anchor="w", pady=(0, 3))
        self.lbl_roi = ttk.Label(
            sec3,
            text="Hay dung chuot keo khoanh vung doi tuong tren hinh ben phai",
            style="Card.TLabel",
            wraplength=330,
            foreground="#ffcc00"
        )
        self.lbl_roi.pack(anchor="w", pady=3)

        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # Section 4: Process Controls & Progress
        sec4 = ttk.Frame(left_frame, style="Card.TFrame")
        sec4.pack(fill="x", padx=12, pady=5)

        ttk.Label(sec4, text="4. Tiến Độ & Thực Thi Xử Lý", style="Header.TLabel").pack(anchor="w", pady=(0, 3))

        self.lbl_status = ttk.Label(sec4, text="Trạng thái: Sẵn sàng", style="Status.TLabel", wraplength=330)
        self.lbl_status.pack(anchor="w", pady=(2, 4))

        self.progress_bar = ttk.Progressbar(sec4, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 8))

        self.btn_start = ttk.Button(
            sec4, text="BẮT ĐẦU XỬ LÝ VIDEO", style="Accent.TButton", command=self._start_process_thread
        )
        self.btn_start.pack(fill="x", pady=3)

        self.btn_stop = ttk.Button(
            sec4, text="DỪNG XỬ LÝ KHẨN CẤP", style="Stop.TButton", command=self._stop_process, state="disabled"
        )
        self.btn_stop.pack(fill="x", pady=3)

        # --- RIGHT PANEL CANVAS ---
        sec_right_top = ttk.Frame(right_frame, style="Card.TFrame")
        sec_right_top.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec_right_top, text="Kéo ROI | Xem trước:", style="Card.TLabel").pack(side="left", padx=(0, 4))

        self.btn_seek_back = ttk.Button(sec_right_top, text="⏪ -5s", width=6, command=lambda: self._seek_relative(-5.0))
        self.btn_seek_back.pack(side="left", padx=2)

        self.btn_play_pause = ttk.Button(sec_right_top, text="▶ Play", width=8, command=self._toggle_play_preview)
        self.btn_play_pause.pack(side="left", padx=2)

        self.btn_seek_forward = ttk.Button(sec_right_top, text="⏩ +5s", width=6, command=lambda: self._seek_relative(5.0))
        self.btn_seek_forward.pack(side="left", padx=2)

        self.slider_frame = ttk.Scale(sec_right_top, from_=0, to=100, orient="horizontal", command=self._on_slider_move)
        self.slider_frame.pack(side="right", fill="x", expand=True, padx=8)

        self.canvas_frame = ttk.Frame(right_frame, style="Card.TFrame")
        self.canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#11111b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Kích hoạt hiển thị chế độ mặc định sau khi toàn bộ widget đã tạo xong
        self._on_mode_change()

    def _browse_video(self):
        initial_dir = os.path.join(ROOT_DIR, "samples") if os.path.exists(os.path.join(ROOT_DIR, "samples")) else None
        file_path = filedialog.askopenfilename(
            title="Chon File Video",
            initialdir=initial_dir,
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            info = VideoProcessor.get_video_info(file_path)
        except Exception as err:
            messagebox.showerror("Lỗi", f"Không thể mở video: {err}")
            return

        self._pause_preview()
        self.video_path = file_path
        self.lbl_filename.config(text=os.path.basename(file_path))

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(file_path)
        self.total_frames = info["total_frames"]
        self.fps = info["fps"]
        self.orig_w = info["width"]
        self.orig_h = info["height"]

        self.lbl_info.config(
            text=f"Độ phân giải: {self.orig_w}x{self.orig_h} | FPS: {self.fps:.1f}\n"
                 f"Thời lượng: {info['duration_sec']:.1f}s ({self.total_frames} frames)"
        )

        self.slider_frame.config(from_=0, to=max(0, self.total_frames - 1))
        self.slider_frame.set(0)

        self.roi = None
        self.lbl_roi.config(
            text="Hay dung chuot keo khoanh vung doi tuong tren hinh ben phai", foreground="#ffcc00"
        )

        self._load_frame(0)

    def _load_frame(self, frame_idx: int):
        if not self.cap or not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx = frame_idx
            self.current_frame_img = frame
            self._redraw_canvas()

    def _toggle_play_preview(self):
        if self.is_playing_preview:
            self._pause_preview()
        else:
            self._play_preview()

    def _play_preview(self):
        if not self.cap or not self.cap.isOpened() or self.is_processing:
            return
        if self.current_frame_idx >= self.total_frames - 1:
            self._load_frame(0)
            self.slider_frame.set(0)
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        self.is_playing_preview = True
        self.btn_play_pause.config(text="⏸ Pause")
        self._next_preview_frame()

    def _pause_preview(self):
        self.is_playing_preview = False
        if self.preview_timer_id is not None:
            self.root.after_cancel(self.preview_timer_id)
            self.preview_timer_id = None
        if hasattr(self, 'btn_play_pause'):
            self.btn_play_pause.config(text="▶ Play")

    def _next_preview_frame(self):
        if not self.is_playing_preview or self.is_processing or not self.cap or not self.cap.isOpened():
            self._pause_preview()
            return

        t_start = time.perf_counter()

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self._pause_preview()
            return

        self.current_frame_idx += 1
        if self.current_frame_idx >= self.total_frames:
            self._pause_preview()
            return

        self.current_frame_img = frame
        self.slider_frame.set(self.current_frame_idx)
        self._redraw_canvas()
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        target_delay_ms = (1000.0 / self.fps) if self.fps > 0 else 33.3
        remaining_delay_ms = max(1, int(target_delay_ms - t_elapsed_ms))

        self.preview_timer_id = self.root.after(remaining_delay_ms, self._next_preview_frame)

    def _seek_relative(self, seconds: float):
        if not self.cap or self.total_frames <= 0:
            return
        frame_delta = int(seconds * self.fps) if self.fps > 0 else int(seconds * 30)
        target_frame = max(0, min(self.total_frames - 1, self.current_frame_idx + frame_delta))
        self.slider_frame.set(target_frame)
        self._load_frame(target_frame)

    def _on_mode_change(self, event=None):
        if not hasattr(self, 'combo_mode') or not hasattr(self, 'enhance_frame'):
            return

        mode_idx = self.combo_mode.current()
        selected_mode = ProcessingMode.ALL_MODES[mode_idx] if mode_idx < len(ProcessingMode.ALL_MODES) else ProcessingMode.INPAINT

        if selected_mode == ProcessingMode.ENHANCE_LIGHT:
            self.enhance_frame.pack(fill="x", pady=5)
            if hasattr(self, 'lbl_roi'):
                self.lbl_roi.config(
                    text="Chế độ Tăng Sáng: Kéo chuột khoanh ô để chọn VÙNG CHỈ ĐỊNH cần tăng sáng.",
                    foreground="#00ffaa"
                )
        else:
            self.enhance_frame.pack_forget()
            if hasattr(self, 'lbl_roi'):
                self.lbl_roi.config(
                    text="Hãy dùng chuột kéo khoanh vùng đối tượng trên hình bên phải",
                    foreground="#ffcc00"
                )
        if hasattr(self, 'canvas'):
            self._redraw_canvas()

    def _on_shadow_lift_change(self, val):
        if hasattr(self, 'lbl_val_shadow_lift'):
            self.lbl_val_shadow_lift.config(text=str(int(float(val))))
        self._on_enhance_param_change()

    def _on_dark_boost_change(self, val):
        if hasattr(self, 'lbl_val_dark_boost'):
            self.lbl_val_dark_boost.config(text=str(int(float(val))))
        self._on_enhance_param_change()

    def _on_clahe_change(self, val):
        if hasattr(self, 'lbl_val_clahe'):
            self.lbl_val_clahe.config(text=str(int(float(val))))
        self._on_enhance_param_change()

    def _on_sharpen_change(self, val):
        if hasattr(self, 'lbl_val_sharpen'):
            self.lbl_val_sharpen.config(text=str(int(float(val))))
        self._on_enhance_param_change()

    def _on_enhance_param_change(self):
        if not self.is_processing and self.current_frame_img is not None:
            self._redraw_canvas()

    def _get_effective_exclude_roi(self):
        """Lấy vùng camera phụ cần bảo vệ (Exclude ROI)."""
        if hasattr(self, 'var_auto_protect_pip') and self.var_auto_protect_pip.get():
            w = self.orig_w
            h = self.orig_h
            if w > 0 and h > 0:
                pw = int(w * 0.35)
                ph = int(h * 0.40)
                px = w - pw
                py = 0
                return (px, py, pw, ph)
        return None

    def _on_slider_move(self, val: str):
        if self.is_processing:
            return
        frame_idx = int(float(val))
        if frame_idx != self.current_frame_idx:
            self._load_frame(frame_idx)

    def _on_canvas_resize(self, event):
        if self.current_frame_img is not None:
            self._redraw_canvas()

    def _redraw_canvas(self):
        if self.current_frame_img is None:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        scale_w = cw / self.orig_w
        scale_h = ch / self.orig_h
        scale = min(scale_w, scale_h)

        disp_w = int(self.orig_w * scale)
        disp_h = int(self.orig_h * scale)

        self.disp_scale_w = self.orig_w / disp_w
        self.disp_scale_h = self.orig_h / disp_h

        self.offset_x = (cw - disp_w) // 2
        self.offset_y = (ch - disp_h) // 2

        # Kiểm tra chế độ ENHANCE_LIGHT để hiển thị live preview
        mode_idx = self.combo_mode.current()
        selected_mode = ProcessingMode.ALL_MODES[mode_idx] if mode_idx < len(ProcessingMode.ALL_MODES) else ProcessingMode.INPAINT

        frame_to_disp = self.current_frame_img
        if selected_mode == ProcessingMode.ENHANCE_LIGHT:
            exclude = self._get_effective_exclude_roi()
            scope = self.var_enhance_scope.get() if hasattr(self, 'var_enhance_scope') else "target_roi"
            target_r = self.roi if scope == "target_roi" else None

            dark_b = float(self.scale_dark_boost.get())
            clahe_v = float(self.scale_clahe.get())
            sharpen_v = float(self.scale_sharpen.get())
            shadow_l = float(self.scale_shadow_lift.get()) if hasattr(self, 'scale_shadow_lift') else 40.0

            frame_to_disp = VideoProcessor.enhance_lighting_and_contrast(
                frame=self.current_frame_img,
                dark_boost=dark_b,
                clahe_amount=clahe_v,
                sharpen_amount=sharpen_v,
                shadow_lift=shadow_l,
                target_roi=target_r,
                exclude_roi=exclude
            )

        resized_bgr = cv2.resize(frame_to_disp, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)
        rgb_img = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        resized_img = Image.fromarray(rgb_img)

        self.display_image = ImageTk.PhotoImage(resized_img)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.display_image)

        if selected_mode == ProcessingMode.ENHANCE_LIGHT:
            scope = self.var_enhance_scope.get() if hasattr(self, 'var_enhance_scope') else "target_roi"
            if scope == "target_roi" and self.roi:
                rx, ry, rw, rh = self.roi
                cx1 = self.offset_x + int(rx / self.disp_scale_w)
                cy1 = self.offset_y + int(ry / self.disp_scale_h)
                cx2 = cx1 + int(rw / self.disp_scale_w)
                cy2 = cy1 + int(rh / self.disp_scale_h)
                self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#00ffaa", width=3, tag="roi")
                self.canvas.create_text(cx1 + 5, cy1 + 5, anchor="nw", text="[Vùng Kích Sáng Cụ Thể]", fill="#00ffaa", font=("Segoe UI", 9, "bold"))

            exclude = self._get_effective_exclude_roi()
            if exclude:
                ex, ey, ew, eh = exclude
                cx1 = self.offset_x + int(ex / self.disp_scale_w)
                cy1 = self.offset_y + int(ey / self.disp_scale_h)
                cx2 = cx1 + int(ew / self.disp_scale_w)
                cy2 = cy1 + int(eh / self.disp_scale_h)
                self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#ff4444", width=3, dash=(6, 4), tag="exclude_roi")
                self.canvas.create_text(cx1 + 5, cy1 + 5, anchor="nw", text="[Camera Phụ - Khóa Sáng]", fill="#ff4444", font=("Segoe UI", 9, "bold"))
        elif self.roi:
            rx, ry, rw, rh = self.roi
            cx1 = self.offset_x + int(rx / self.disp_scale_w)
            cy1 = self.offset_y + int(ry / self.disp_scale_h)
            cx2 = cx1 + int(rw / self.disp_scale_w)
            cy2 = cy1 + int(rh / self.disp_scale_h)
            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#00ffaa", width=3, tag="roi")

    def _on_mouse_down(self, event):
        if self.current_frame_img is None or self.is_processing:
            return
        self.start_x = event.x
        self.start_y = event.y
        self.canvas.delete("roi")

    def _on_mouse_drag(self, event):
        if self.start_x is None or self.start_y is None or self.is_processing:
            return
        self.canvas.delete("roi")
        self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="#00ffaa", width=2, tag="roi")

    def _on_mouse_up(self, event):
        if self.start_x is None or self.start_y is None or self.is_processing:
            return

        end_x, end_y = event.x, event.y

        x1 = min(self.start_x, end_x) - self.offset_x
        y1 = min(self.start_y, end_y) - self.offset_y
        x2 = max(self.start_x, end_x) - self.offset_x
        y2 = max(self.start_y, end_y) - self.offset_y

        w = x2 - x1
        h = y2 - y1

        if w < 5 or h < 5:
            self.roi = None
            self.lbl_roi.config(text="Kích thước quá nhỏ. Hãy kéo chọn lại!", foreground="#ff5555")
            self._redraw_canvas()
            return

        orig_x = int(x1 * self.disp_scale_w)
        orig_y = int(y1 * self.disp_scale_h)
        orig_w = int(w * self.disp_scale_w)
        orig_h = int(h * self.disp_scale_h)

        orig_x = max(0, min(orig_x, self.orig_w - 1))
        orig_y = max(0, min(orig_y, self.orig_h - 1))
        orig_w = min(orig_w, self.orig_w - orig_x)
        orig_h = min(orig_h, self.orig_h - orig_y)

        self.roi = (orig_x, orig_y, orig_w, orig_h)
        self.lbl_roi.config(text=f"Vùng kích sáng chỉ định: X={orig_x}, Y={orig_y}, W={orig_w}, H={orig_h}", foreground="#00ffaa")

        self.start_x = None
        self.start_y = None
        self._redraw_canvas()

    def _start_process_thread(self):
        if not self.video_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file video đầu vào trước!")
            return

        mode_idx = self.combo_mode.current()
        mode_keys = ProcessingMode.ALL_MODES
        selected_mode = mode_keys[mode_idx] if mode_idx < len(mode_keys) else ProcessingMode.INPAINT

        if not self.roi and selected_mode not in (ProcessingMode.CROP, ProcessingMode.ENHANCE_LIGHT):
            messagebox.showwarning("Cảnh báo", "Vui lòng khoanh vùng đối tượng trên hình trước khi bắt đầu!")
            return

        self._pause_preview()
        self.is_processing = True
        self.stop_requested = False

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.slider_frame.config(state="disabled")
        self.lbl_status.config(text="Trạng thái: Đang xử lý video...", foreground="#00d2ff")

        thread = threading.Thread(target=self._run_video_processing, daemon=True)
        thread.start()

    def _stop_process(self):
        if self.is_processing:
            self.stop_requested = True
            self.lbl_status.config(text="Trạng thái: Đang dừng xử lý...", foreground="#ff5555")

    def _run_video_processing(self):
        try:
            mode_idx = self.combo_mode.current()
            mode = ProcessingMode.ALL_MODES[mode_idx] if mode_idx < len(ProcessingMode.ALL_MODES) else ProcessingMode.INPAINT
            padding = int(self.spin_padding.get())

            dark_boost = float(self.scale_dark_boost.get()) if hasattr(self, 'scale_dark_boost') else 50.0
            clahe_amount = float(self.scale_clahe.get()) if hasattr(self, 'scale_clahe') else 40.0
            sharpen_amount = float(self.scale_sharpen.get()) if hasattr(self, 'scale_sharpen') else 20.0
            shadow_lift = float(self.scale_shadow_lift.get()) if hasattr(self, 'scale_shadow_lift') else 40.0

            scope = self.var_enhance_scope.get() if hasattr(self, 'var_enhance_scope') else "target_roi"
            target_r = self.roi if (mode == ProcessingMode.ENHANCE_LIGHT and scope == "target_roi") else None
            exclude_r = self._get_effective_exclude_roi() if mode == ProcessingMode.ENHANCE_LIGHT else self.roi

            try:
                start_t = float(self.entry_start_time.get().strip() or 0.0)
            except ValueError:
                start_t = 0.0

            end_t_str = self.entry_end_time.get().strip()
            try:
                end_t = float(end_t_str) if end_t_str else None
            except ValueError:
                end_t = None

            def gui_progress(pct: float, current: int, total: int):
                self.root.after(0, self._update_progress, pct, current, total)

            def check_cancelled() -> bool:
                return self.stop_requested

            output_path = VideoProcessor.process_video(
                video_path=self.video_path,
                mode=mode,
                roi=self.roi,
                padding=padding,
                start_time=start_t,
                end_time=end_t,
                dark_boost=dark_boost,
                clahe_amount=clahe_amount,
                sharpen_amount=sharpen_amount,
                shadow_lift=shadow_lift,
                target_roi=target_r,
                exclude_roi=exclude_r,
                progress_callback=gui_progress,
                stop_checker=check_cancelled
            )

            if self.stop_requested:
                self.root.after(0, self._finish_processing, False, "Đã hủy theo yêu cầu!")
            else:
                self.root.after(0, self._finish_processing, True, output_path)

        except Exception as err:
            self.root.after(0, self._finish_processing, False, str(err))

    def _update_progress(self, pct: float, frame_count: int, total: int):
        self.progress_bar['value'] = pct
        self.lbl_status.config(text=f"Tiến độ: {pct:.1f}% ({frame_count}/{total} frames)")

    def _finish_processing(self, success: bool, result_msg: str):
        self.is_processing = False
        self.stop_requested = False

        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.slider_frame.config(state="normal")

        if success:
            self.lbl_status.config(text="ĐÃ HOÀN THÀNH XUẤT VIDEO!", foreground="#00ffaa")
            messagebox.showinfo("Thành Công", f"Đã xuất video thành công tại:\n{result_msg}")
        else:
            self.lbl_status.config(text=f"Đã dừng / Lỗi: {result_msg}", foreground="#ff5555")


def main():
    root = tk.Tk()
    app = VideoObjectRemoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
