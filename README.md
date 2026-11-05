# 🎬 Công Cụ Xóa & Che Đối Tượng Video (Video Object Remover & Masker)

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![Architecture](https://img.shields.io/badge/Architecture-MVP-orange.svg)
![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)

Ứng dụng xử lý video đa năng hỗ trợ **xóa, che và làm mờ đối tượng di động** trong video sử dụng OpenCV, Object Tracking (MIL Tracker) và Inpainting. 

Được cấu trúc theo mô hình **MVP (Model-View-Presenter)** và chuẩn **Standard Python Project Layout**, ứng dụng hỗ trợ cả **Giao diện Đồ họa (GUI Tkinter)** và **Công cụ Dòng lệnh (CLI)**.

---

## 🌟 Tính Năng Nổi Bật

- 🎨 **4 Chế độ xử lý phong phú:**
  - **`Inpaint`:** Xóa đối tượng và tự động tái tạo nền phía sau (Alexandru Telea Method).
  - **`Masking`:** Phủ khối màu tối bảo mật đè lên đối tượng.
  - **`Blur`:** Làm mờ mạnh đối tượng (Gaussian Blur 99x99).
  - **`Crop`:** Cắt bỏ viền lề video chứa đối tượng.
- ⚡ **Cắt / Giới hạn khoảng thời gian xử lý (Time-Range Trimming):** Cho phép đặt thời gian bắt đầu (`start_time`) và kết thúc (`end_time`) để chạy thử nghiệm siêu tốc trên video nặng (xử lý 10s test chỉ trong 2-3s).
- 🎬 **Bộ xem trước Video mượt mà (Preview Player 30 FPS):** Tích hợp nút `▶ Play / ⏸ Pause`, `⏪ -5s`, `⏩ +5s` và thanh trượt timeline giúp bạn chọn đúng hình ảnh để khoanh vùng. Render bằng OpenCV C++ Bilinear Resize siêu tốc (0.5ms/frame).
- 📊 **Tiến độ phần trăm Realtime:** Thanh Progress Bar & con số `%` nhảy liên tục theo từng khung hình giúp bạn biết chính xác thời gian hoàn thành.
- 🛡️ **An toàn dữ liệu tuyệt đối:** Video gốc luôn mở ở chế độ Read-Only, video kết quả tự động lưu thành file mới trong thư mục `outputs/` *(không bao giờ bị ghi đè hay mất file gốc)*.

---

## 📂 Cấu Trúc Thư Mục Dự Án

```
chinhsuavideodc/
├── main.py                     # 🚀 File chạy chính (GUI & CLI)
├── requirements.txt            # 📦 Danh sách thư viện phụ thuộc Python
├── README.md                  # 📖 Tài liệu hướng dẫn sử dụng
├── .gitignore                 # 🚫 Khai báo loại trừ file tạm & video nặng
│
├── src/                        # 📁 Mã nguồn chính của ứng dụng
│   ├── core/                   # 🧠 [Model] Thuật toán OpenCV & MIL Object Tracking
│   │   └── video_processor.py
│   ├── gui/                    # 🎨 [View/Presenter] Giao diện người dùng Tkinter
│   │   └── app_gui.py
│   └── cli/                    # 💻 [CLI] Công cụ dòng lệnh
│       └── video_object_remover.py
│
├── docs/                       # 📑 Tài liệu kỹ thuật & Handover
│   └── ARCHITECTURE.md
│
├── samples/                    # 🎞️ Thư mục lưu dữ liệu video mẫu thử nghiệm
└── outputs/                    # 📤 Thư mục tự động lưu trữ các video kết quả xuất ra
```

---

## 📦 Cài Đặt Phụ Thuộc

Yêu cầu Python version **3.8+**. Cài đặt các thư viện cần thiết bằng `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🚀 Hướng Dẫn Sử Dụng

### 1. Khởi Chạy Giao Diện Đồ Họa (GUI)

Khởi chạy bằng file entry point ở thư mục gốc:

```bash
python main.py
```

*(Hoặc chạy trực tiếp `python src/gui/app_gui.py`)*

**Các bước thao tác:**
1. Nhấn nút **`Mở File Video...`** để chọn video đầu vào (ví dụ các file trong thư mục `samples/`).
2. Sử dụng các nút xem trước **`▶ Play / ⏸ Pause`**, **`⏪ -5s`**, **`⏩ +5s`** hoặc thanh trượt để đến thời điểm có đối tượng cần che/xóa.
3. Dùng chuột **kéo thả chọn khung hình chữ nhật (ROI màu xanh lá)** bao quanh đối tượng trên hình ảnh bên phải.
4. *(Tùy chọn)* Nhập khoảng thời gian cần test tại mục **Cắt video: Từ (s) - Đến (s)** (ví dụ: `Từ: 0.0` `Đến: 15` để xử lý thử 15 giây đầu).
5. Chọn **Chế độ xử lý** (`Inpaint`, `Masking`, `Blur`, `Crop`) và điều chỉnh **Padding**.
6. Nhấn nút màu xanh **`BẮT ĐẦU XỬ LÝ VIDEO`**. Thanh tiến độ % sẽ nhảy nhảy theo thời gian thực và file kết quả sẽ tự động được lưu vào thư mục `outputs/`.

---

### 2. Ghép Nối Nhiều Video Thành 1 Video

#### Cách 1: Sử dụng Giao diện GUI (Tab 2)
1. Khởi chạy `python main.py`.
2. Chuyển sang tab **`🎞️ 2. Ghép Nối Nhiều Video (Merger)`**.
3. Nhấn **`➕ Thêm Video...`** để chọn các file video cần ghép.
4. Sử dụng các nút **`⬆️ Di Chuyển Lên`**, **`⬇️ Di Chuyển Xuống`**, **`❌ Xóa Đã Chọn`** để sắp xếp thứ tự ghép mong muốn.
5. Lựa chọn **Độ phân giải đầu ra** (Tự động, Full HD 1080p, 720p, 4K, 9:16), bật/tắt **Letterbox** và gắn **Timeline OSD**.
6. Nhấn **`🚀 BẮT ĐẦU GHÉP VIDEO`**.

#### Cách 2: Sử dụng Dòng Lệnh (CLI)
```bash
# Ghép nhanh danh sách video bằng script tiện ích merge_videos.py
python merge_videos.py -i video1.mp4 video2.mp4 video3.mp4 -o outputs/merged_output.mp4

# Ghép video với chuẩn hóa kích thước 1080p Full HD và gắn Timeline OSD
python merge_videos.py -i video1.mp4 video2.mp4 -W 1920 -H 1080 --timeline --timeline-mode elapsed

# Hoặc sử dụng qua entry point main.py
python main.py --cli --concat video1.mp4 video2.mp4 --output outputs/merged_video.mp4
```

---

### 3. Khởi Chạy Công Cụ Dòng Lệnh Xóa / Che Đối Tượng (CLI)

Sử dụng cờ `--cli` khi chạy file `main.py`:

```bash
# Xử lý xóa đối tượng (Inpaint) và khoanh vùng chọn bằng chuột trên cửa sổ OpenCV
python main.py --cli --input samples/sample1.mp4 --mode inpaint

# Chạy thử 10 giây đầu (--start-time 0 --end-time 10) làm mờ đối tượng (Blur) với ROI chọn sẵn
python main.py --cli --input samples/sample1.mp4 --mode blur --roi 100 150 200 250 --start-time 0 --end-time 10

# Cắt lề video (Crop)
python main.py --cli --input samples/sample1.mp4 --mode crop --roi 400 0 100 100
```

---

## 📐 Tài Liệu Kỹ Thuật & Handover

Chi tiết mô hình kiến trúc MVP, sơ đồ luồng dữ liệu Mermaid (Dataflow Diagram), thông số tối ưu hiệu năng render canvas 30 FPS và nhật ký chuyển giao v1.2.0 được ghi nhận chi tiết tại: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).