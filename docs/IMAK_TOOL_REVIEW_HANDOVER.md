## Kết luận tổng quan

Kế hoạch mô tả tốt một MVP thử nghiệm, nhưng chưa đủ an toàn để triển khai pilot trong nhà máy. Hai blocker lớn nhất là:

1. `nakazasen-ai-router` v0.5.1 chưa truyền được keyframe theo định dạng ảnh đa phương thức như kiến trúc đang giả định.
2. Mục tiêu xử lý video 3 phút trong dưới 60 giây mâu thuẫn với tiêu chí Pose chỉ đạt 15 FPS nếu xử lý toàn bộ frame.

### Bảng tổng hợp

| Tiêu chí | Đánh giá | Phát hiện chính | Mức rủi ro |
|---|---|---|---|
| Định nghĩa bài toán | Khá | Mục tiêu và output rõ, nhưng thiếu phạm vi camera, số người, điều kiện môi trường và định nghĩa ground truth | Cao |
| Pseudocode/thuật toán | Trung bình | EMA, velocity và Muda có thể triển khai; One Euro Filter, cycle boundary và quality gating chưa đủ | Cao |
| JSON schema | Chưa đạt | Mới là JSON mẫu, chưa phải JSON Schema; thiếu confidence, provenance, cycle boundaries và kiểu dữ liệu nhất quán | Cao |
| Khả thi trên i5-8265U | Có điều kiện | OpenCV/EMA/SSIM ổn; MediaPipe khả thi khi resize + frame sampling; SLA dưới 60 giây chưa thực tế | Cao |
| Cycle segmentation | Chưa tin cậy | Autocorrelation hiện tại dễ chọn harmonic, lag giả và không xử lý chu kỳ biến thiên | Rất cao |
| Router API | Đúng một phần | Import và factory đúng; multimodal, thứ tự fallback, result fields và metadata task đang sai | Rất cao |
| Privacy | Chưa đạt | Không thể coi ảnh là `cloud_safe` chỉ vì đã nén; router không tự kiểm tra nội dung | Rất cao |
| Kiến trúc module | Khá | 7 module hợp lý cho MVP, nhưng cần quality/privacy layer và tách trách nhiệm decode/keyframe | Trung bình |
| Roadmap 4 tuần | Quá lạc quan | Có thể làm demo có kiểm soát; khó đạt đồng thời accuracy, performance, privacy và E2E QA | Cao |
| Dependency/reproducibility | Chưa đạt | Thiếu package, không pin phiên bản, có dependency thừa | Cao |

---

## 1. Tính đầy đủ

### Định nghĩa bài toán

Các functional requirement tại [IMPLEMENTATION_PLAN.md](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:33) mô tả khá rõ luồng chính: video → pose → motion/Muda → cycle → VLM → PowerPoint.

Tuy nhiên, kế hoạch chưa khóa các giả định ảnh hưởng trực tiếp đến độ chính xác:

- Một hay nhiều công nhân trong khung hình.
- Camera cố định hay cầm tay; góc nghiêng tối đa và khoảng cách tới công nhân.
- Có yêu cầu thấy toàn thân hay chỉ thân trên.
- Định nghĩa “idle/Muda”: tay đứng yên chưa chắc là lãng phí, có thể là giữ chi tiết, kiểm tra chất lượng hoặc chờ máy theo tiêu chuẩn.
- Chu kỳ ngắn nhất/dài nhất và số chu kỳ tối thiểu trong video.
- Cách đo tiêu chí “nhận diện đúng ≥85%”: frame accuracy, event precision/recall hay temporal IoU với dung sai bao nhiêu giây.
- Chính sách lưu trữ/xóa video, keyframe và báo cáo.
- Mô hình vận hành: một người dùng, nhiều job đồng thời, offline hay bắt buộc cloud.

Vì vậy, đây mới là định nghĩa MVP kỹ thuật, chưa phải specification có thể nghiệm thu khách quan.

### Mức đầy đủ của thuật toán

- EMA có công thức và pseudocode đủ cơ bản.
- Tài liệu nói “EMA kết hợp One Euro Filter” nhưng không có công thức hay pseudocode One Euro Filter tại [dòng 180–197](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:180).
- Velocity chưa xử lý landmark mất, visibility/presence thấp, timestamp không đều hoặc frame bị drop.
- Muda dùng điều kiện `all(v < threshold)`, nên chỉ một mẫu nhiễu cũng phá vỡ segment; chưa có hysteresis, gap filling hoặc minimum valid-landmark ratio.
- Phần cycle nói dùng local minima để xác định boundary nhưng pseudocode chỉ trả về một `cycle_time_sec`, hoàn toàn chưa trả về các cycle segment.
- Keyframe selector chọn “frame hợp lệ đầu tiên”, chưa tối ưu độ đại diện theo cycle, Muda event hoặc phase của thao tác.

### JSON schema

Hai đoạn ở [motion schema](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:373) và [Kaizen schema](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:401) chỉ là example JSON, chưa có `required`, `enum`, giới hạn giá trị, nullable policy hay version.

Các thiếu sót đáng chú ý:

- `resolution` nên là `{width: integer, height: integer}`, không nên là chuỗi.
- `avg_cycle_time` và phần trăm trong output AI nên là số, không phải `"28.5s"` hoặc `"6.8%"`.
- Thiếu `schema_version`, `analysis_id`, algorithm/model version và bộ tham số đã sử dụng.
- Thiếu danh sách `cycles[{start_sec,end_sec,duration_sec,confidence}]`.
- Thiếu chất lượng Pose: coverage, mean visibility, số frame bị mất, multi-person warning.
- Thiếu confidence và evidence cho từng good/problem point.
- Action item thiếu owner, deadline, expected benefit và trạng thái xác minh.
- Chưa định nghĩa `end_frame/end_sec` là inclusive hay exclusive.
- Không có schema riêng cho request chứa keyframe, MIME type, kích thước và hash.

Nên dùng JSON Schema hoặc Pydantic model và validate cả input lẫn output.

---

## 2. Tính khả thi kỹ thuật

### Hiệu năng trên i5-8265U

OpenCV, EMA, velocity, Muda và SSIM đều nhẹ nếu xử lý streaming và resize ảnh. MediaPipe Pose có CPU delegate và chế độ video; GPU delegate Python hiện bị giới hạn chủ yếu trên Ubuntu, nên chọn CPU trên Windows/Intel UHD 620 là đúng. MediaPipe cũng mặc định `num_poses=1`; nhiều người phải cấu hình riêng và sẽ tăng tải. [Google PoseLandmarker options](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/PoseLandmarkerOptions), [BaseOptions delegate](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/BaseOptions).

Điểm bất khả thi nằm ở SLA:

- Video 3 phút, 30 FPS có 5.400 frame.
- Nếu Pose chạy 15 inference FPS thì riêng bước Pose cần khoảng `5400 / 15 = 360 giây`.
- Muốn hoàn tất toàn pipeline dưới 60 giây, throughput toàn hệ thống phải tương đương trên 90 frame/giây nếu xử lý mọi frame.

Do đó tiêu chí tại [dòng 483](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:483) và [dòng 509](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:509) mâu thuẫn nhau.

Mục tiêu dưới 60 giây chỉ có thể xem xét khi:

- Decode một lần theo streaming.
- Resize xuống khoảng 640p hoặc crop ROI.
- Chạy Pose ở 3–8 sampled FPS.
- Dùng video tracking mode, không detect lại độc lập từng frame.
- Không giữ toàn bộ frame 4K trong RAM.
- Benchmark thực tế trước khi chốt SLA.

### Đánh giá các tham số

| Tham số | Nhận xét |
|---|---|
| `alpha=0.35` | Hợp lý làm giá trị khởi đầu, nhưng độ trễ theo thời gian thay đổi theo FPS; cần chuyển sang smoothing dựa trên timestamp hoặc hiệu chỉnh theo FPS |
| `V_idle=0.04` | Rủi ro cao vì tọa độ chuẩn hóa theo chiều ảnh, không theo kích thước cơ thể; camera zoom/góc quay sẽ đổi vận tốc tương đối |
| `T_idle_min=1.5s` | Có thể dùng cho pilot, nhưng dễ false positive với thao tác giữ/ép/chờ máy hợp lệ và false negative với nhiều micro-waste ngắn |
| `SSIM=0.80` | Chỉ là heuristic; dễ bị ảnh hưởng bởi rung camera, ánh sáng, background và thay đổi vị trí công nhân |
| `blur_thresh=100` | Phụ thuộc độ phân giải, resize, nhiễu và ánh sáng; không nên dùng chung cho 720p–4K |

Nên chuẩn hóa vận tốc theo shoulder width/torso size, chỉ dùng landmark đủ visibility, thêm hysteresis và hiệu chỉnh threshold trên video đã gán nhãn.

### Autocorrelation Cycle Time Segmentation

Thuật toán hiện tại tại [dòng 261–285](/D:/Sandbox/chinhsuavideodc/IMPLEMENTATION_PLAN.md:261) chưa đủ tin cậy cho video nhà máy thực tế vì:

- `np.argmax` không tìm “đỉnh cực đại cục bộ đầu tiên” như mô tả; nó tìm giá trị lớn nhất trên toàn vùng lag.
- Autocorrelation chưa normalize theo số mẫu chồng lấp, nên bị bias theo lag.
- Có thể chọn harmonic: nửa chu kỳ, gấp đôi chu kỳ hoặc chu kỳ của một động tác con.
- Không có peak prominence/confidence hay kiểm tra độ ổn định theo các cửa sổ thời gian.
- Không xử lý chu kỳ thay đổi do công nhân chậm dần, lỗi sản phẩm hoặc rework.
- Không hoạt động tốt khi video chỉ có 1–2 cycle, có nhiều loại sản phẩm hoặc nhiều người.
- `np.correlate` là \(O(N^2)\); không cần thiết cho video dài.
- Nếu chuỗi ngắn hơn `min_cycle_sec`, đoạn `argmax` có thể lỗi vì mảng rỗng.

Nên dùng FFT autocorrelation đã normalize, giới hạn `[min_cycle,max_cycle]`, peak prominence, kiểm tra harmonic và stability theo cửa sổ. Boundary nên xác định bằng phase/event alignment hoặc template/DTW, không chỉ local minima vận tốc.

---

## 3. Tích hợp `nakazasen-ai-router`

### Những phần đúng

Các import `AIRequest`, `RouterPolicy`, `create_router_from_env`, cùng các tham số `env`, `provider_names`, `enable_network` và `policy` đều tồn tại trong API v0.5.1. Factory không tự bật network, nên `enable_network=True` là cần thiết. [Public API contract](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/docs/public_api.md), [config.py v0.5.1](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/src/nakazasen_ai_router/config.py#L26-L46).

### Các lỗi API/behavior quan trọng

1. **Router không hỗ trợ keyframe đa phương thức theo kế hoạch.**  
   `AIRequest` chỉ có `prompt: str` và `metadata`. Adapter v0.5.1 dựng `/chat/completions` với message content là chuỗi, thậm chí ép `content` qua `str()`. Không có image content block hoặc Gemini-native image part. [AIRequest/AIResult source](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/src/nakazasen_ai_router/core.py#L64-L78), [OpenAI-compatible adapter](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/src/nakazasen_ai_router/providers/openai_compatible.py#L195-L207), [message conversion](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/src/nakazasen_ai_router/providers/openai_compatible.py#L327-L338).

   Base64 nhét vào prompt chỉ là văn bản lớn, không biến nó thành ảnh VLM. Đây là blocker kiến trúc.

2. **Thứ tự Gemini → OpenRouter → Groq không được đảm bảo chỉ bằng `provider_names`.**  
   Router sắp candidate theo last-resort, routing score và priority; `routing_mode="balanced"` mặc định có thể thay đổi thứ tự. [Candidate ordering](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/src/nakazasen_ai_router/core.py#L614-L620).

3. **Các field kết quả ở dòng 364 là sai.**  
   `AIResult` không có `result.attempts` hay `result.cost_estimate`; dữ liệu nằm trong `result.metadata["attempts"]` và `result.metadata["cost_estimate"]`. Nếu cần outcome có cấu trúc, dùng `route_outcome()`.

4. **Metadata key `task` không được router dùng để routing.**  
   Source đọc `metadata["task_type"]`; vì vậy `"task": "kaizen_video_analysis"` hiện bị bỏ qua.

5. **“JSON enforcement” chưa thực sự được enforce.**  
   Adapter chỉ gửi `model` và `messages`, không gửi `response_format`/JSON Schema. Retry bằng prompt có thể cải thiện nhưng không bảo đảm JSON hợp lệ.

6. **Fallback VLM chưa tương thích.**  
   Groq/OpenRouter model mặc định có thể là text-only. Tất cả candidate trong fallback phải được khóa vào model hỗ trợ vision và cùng message schema.

### Privacy

Không nên mặc định gắn `cloud_safe` cho keyframe chỉ vì ảnh đã nén. Keyframe có thể chứa:

- Khuôn mặt, thẻ nhân viên, tên hoặc màn hình máy.
- Thiết kế sản phẩm, jig/fixture, quy trình độc quyền.
- Serial number, barcode, layout dây chuyền.
- Công nhân hoặc nhà thầu chưa đồng ý truyền dữ liệu ra cloud.

Router chỉ thực thi metadata do host cung cấp; nó không tự kiểm tra nội dung hoặc chứng minh việc phân loại đã đúng. [Privacy boundary chính thức](https://github.com/Nakazasen/nakazasen-ai-router/blob/v0.5.1/README.md#privacy-boundary).

Chính sách phù hợp hơn:

- Mặc định `confidential`.
- Chỉ chuyển `cloud_safe` sau local redaction: crop ROI, blur face/badge/screen, loại metadata và kiểm tra thủ công hoặc policy engine.
- Ghi rõ `contains_raw_evidence=False`, `contains_confidential_files=False`, `sanitized_by`, phiên bản sanitizer.
- Có DPA, retention policy, data residency và danh sách model/provider được phê duyệt.
- Không log prompt chứa Base64 hoặc raw frame.

---

## 4. Kiến trúc và thiết kế

Bảy module là hợp lý cho MVP, nhưng cần điều chỉnh:

- `video_reader` chỉ nên decode, normalize timestamp/orientation và stream frame. Không nên đồng thời chọn keyframe vì đã có `keyframe_selector`.
- `motion_analyzer` đang gom smoothing, feature extraction, Muda và cycle segmentation. Nên tách ít nhất thành signal preprocessing và event/cycle detectors để test độc lập.
- Giữ riêng `router_client` và `ai_kaizen_advisor`: một bên quản lý transport/policy, một bên prompt/schema/repair.
- Bổ sung `quality_gate` để đánh giá ánh sáng, rung camera, pose coverage, số người và confidence.
- Bổ sung `privacy_sanitizer` trước mọi cloud request.
- Dùng shared typed models/config thay vì truyền dictionary tự do giữa module.

Các bottleneck chính:

1. Decode + Pose toàn bộ frame 1080p/4K.
2. Giữ frame trong RAM thay vì stream.
3. Autocorrelation \(O(N^2)\).
4. SSIM toàn ảnh cho nhiều candidate.
5. Encode/upload Base64.
6. Streamlit chạy job dài đồng bộ, dễ timeout hoặc rerun ngoài ý muốn.

Roadmap 4 tuần chỉ khả thi cho demo với một người, camera cố định, video ngắn, frame sampling và đánh giá thủ công. Để đạt acceptance criteria hiện tại, nên dự kiến ít nhất 6–10 tuần, trong đó có riêng một vòng thu thập ground truth, calibration và privacy/security review.

---

## 5. Thiếu sót và rủi ro

Các edge case chưa được xử lý:

- Video tối, backlight, motion blur, PPE che landmark.
- Nhiều người và identity switching.
- Tay ra khỏi khung hoặc bị bàn/chi tiết máy che.
- Camera rung, zoom, pan hoặc video bị xoay/mirror.
- Variable frame rate, frame drop, FPS metadata bằng 0.
- Video hỏng, codec không hỗ trợ, video quá ngắn hoặc không có chu kỳ.
- Chu kỳ dở ở đầu/cuối, rework, nhiều product variant.
- Pose left/right bị đảo hoặc confidence thấp kéo dài.
- Idle hợp lệ bị gắn thành Muda.
- Disk đầy, mất mạng, user hủy job, Streamlit rerun.

Error handling hiện chưa đủ: thiếu input validation, pose-quality fallback, timeout tổng, retry có jitter, cancellation, atomic output, temp-file cleanup, JSON Schema validation và phân biệt lỗi provider với lỗi output AI.

Dependency tại [requirements.txt](/D:/Sandbox/chinhsuavideodc/requirements.txt:1) cũng chưa tái lập được:

- Thiếu `scikit-image`, dù pseudocode import `structural_similarity`.
- Thiếu `nakazasen-ai-router`.
- `google-genai` có vẻ thừa nếu mọi cloud call bắt buộc qua router.
- Tất cả dependency chỉ có lower bound, dễ phát sinh breaking change.
- Nên pin Python 3.10/3.11 và tạo lock file theo Windows x64; MediaPipe hiện công bố hỗ trợ Python 3.9–3.12. [MediaPipe trên PyPI](https://pypi.org/project/mediapipe/).

---

## 6. Tối đa 5 cải tiến ưu tiên cao nhất

1. **P0 – Giải quyết multimodal contract:** mở rộng/custom provider cho structured image parts, hoặc tách VLM transport khỏi router v0.5.1. Thêm integration test thật cho cùng một keyframe qua từng fallback model.

2. **P0 – Thiết lập privacy fail-closed:** mặc định `confidential`, thêm `privacy_sanitizer`, policy phê duyệt cloud và audit metadata; không tự gắn `cloud_safe`.

3. **P1 – Viết lại cycle/Muda thành thuật toán có confidence:** normalized velocity, landmark-quality gating, hysteresis, FFT autocorrelation, harmonic validation và cycle boundaries; xây bộ video ground truth để đo precision/recall/temporal IoU.

4. **P1 – Chuẩn hóa contract và router usage:** dùng Pydantic/JSON Schema; sửa `task_type`, đọc attempts/cost từ `result.metadata`, cấu hình fallback có kiểm thử và validate model capability.

5. **P1 – Benchmark lại roadmap/SLA:** resize + frame sampling + streaming, đo latency từng stage trên đúng i5-8265U; chỉ chốt mục tiêu `<60s` sau benchmark, đồng thời pin dependency bằng lock file.

Ghi chú: bước lập knowledge graph theo skill `graphify` bị chặn vì ổ D: còn 0 byte trống. Review trên được thực hiện trực tiếp theo từng dòng tài liệu và đối chiếu source chính thức đúng tag `v0.5.1`; không có file nguồn nào được chỉnh sửa.
