# IMAK-Tool — Tài liệu bàn giao tổng hợp

Tài liệu này là entry point chính cho việc bàn giao IMAK-Tool (Industrial Motion Analysis & Kaizen Reporting Tool).

## Tài liệu nguồn

### 1. Đặc tả và kế hoạch triển khai

[IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Bao gồm:

- Mục tiêu và functional requirements FR-01 đến FR-07.
- Cấu hình phần cứng i5-8265U / 16 GB RAM / Intel UHD 620.
- Kiến trúc pipeline video → Pose → motion/Muda → cycle → VLM → PPTX.
- Công thức và pseudocode EMA, velocity, acceleration, Muda, autocorrelation và keyframe selection.
- Tích hợp `nakazasen-ai-router`.
- JSON examples cho motion analysis và Kaizen report.
- Cấu trúc module, roadmap 4 phase và acceptance criteria.

### 2. Review kỹ thuật và các điểm phải xử lý

[IMAK_TOOL_REVIEW_HANDOVER.md](./IMAK_TOOL_REVIEW_HANDOVER.md)

Bao gồm:

- Đánh giá completeness và technical feasibility.
- Phân tích hiệu năng thực tế trên CPU không CUDA.
- Rủi ro của các tham số EMA/velocity/Muda/SSIM.
- Hạn chế của Autocorrelation Cycle Time Segmentation.
- Kiểm chứng API `AIRequest`, `RouterPolicy`, `create_router_from_env`.
- Rủi ro multimodal, fallback, privacy và cloud data.
- Edge cases, error handling, dependency và 5 ưu tiên cải tiến.

## Trạng thái bàn giao

**MVP prototype có điều kiện — chưa sẵn sàng pilot nhà máy.**

Hai blocker cần giải quyết trước khi triển khai:

1. Router v0.5.1 hiện chưa có contract truyền image/multimodal keyframe tương ứng với kiến trúc trong kế hoạch.
2. SLA xử lý video 3 phút dưới 60 giây chưa phù hợp nếu chạy Pose trên toàn bộ frame ở khoảng 15 FPS.

## Thứ tự đọc đề xuất

1. Đọc `IMPLEMENTATION_PLAN.md` để hiểu yêu cầu và thiết kế dự kiến.
2. Đọc `IMAK_TOOL_REVIEW_HANDOVER.md` để biết giới hạn, rủi ro và các điểm chưa được chấp nhận.
3. Chỉ bắt đầu implementation sau khi owner xác nhận hai blocker và năm việc ưu tiên P0/P1.

## Lưu ý về tài liệu cũ

[docs/ARCHITECTURE.md](./ARCHITECTURE.md) hiện mô tả phần mềm Video Object Remover & Masker cũ. Không dùng file đó làm đặc tả kiến trúc của IMAK-Tool.

