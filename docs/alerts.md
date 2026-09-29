# Alerts và runbooks

Các rule dưới đây cảnh báo triệu chứng ảnh hưởng người dùng hoặc ngân sách chất lượng. Alert được gửi tới `#day13-llmops-alerts`; nếu triển khai thật, cần nối channel này vào Alertmanager hoặc hệ thống alert tương ứng.

## Alert 1 — User-visible latency elevated

- **Severity:** warning
- **Duration:** 5 phút liên tục
- **Owner:** LLM Platform On-call
- **SLI/SLO:** `fast_successful_requests`, latency tối đa 3 giây trong rolling window 28 ngày.
- **Điều kiện:** `request_latency_p95_ms > 3000` trong 5 phút.
- **Ảnh hưởng:** người dùng phải đợi lâu; SLO latency bắt đầu tiêu error budget.
- **Kiểm tra đầu tiên:**
  1. Mở dashboard và so sánh P50/P95/P99 với TTFT trong cùng time range.
  2. Lọc log `response_sent` theo khoảng thời gian, lấy `correlation_id` của request chậm.
  3. Mở trace tương ứng, so thời lượng retrieval và generation.
- **Mitigation:** giảm tải/concurrency hoặc tạm tắt tính năng nặng; nếu generation chậm, dùng prompt ngắn hơn hoặc giới hạn output tokens. Không rollback prompt chỉ dựa vào latency nếu trace chưa chỉ ra generation.
- **Giải quyết:** khắc phục bước chiếm thời lượng, chạy lại workload an toàn, xác nhận P95 dưới ngưỡng ít nhất 10 phút rồi mới đóng alert.

## Alert 2 — Request failures elevated

- **Severity:** critical
- **Duration:** 5 phút liên tục
- **Owner:** API On-call
- **SLI/SLO:** request lỗi được tính là bad event trong `fast_successful_requests`.
- **Điều kiện:** `request_error_rate_pct > 2` trong 5 phút.
- **Ảnh hưởng:** một phần người dùng không nhận được câu trả lời.
- **Kiểm tra đầu tiên:**
  1. Tách `request_failed` theo `error_type` và `tool_name`.
  2. Theo một `correlation_id` từ log sang trace để xác định observation báo lỗi.
  3. Kiểm tra health/dependency status và thời điểm bắt đầu lỗi.
- **Mitigation:** khôi phục dependency hoặc cấu hình vừa thay đổi; nếu dependency lỗi diện rộng, tạm trả lời bằng fallback có kiểm soát và giữ response status đúng.
- **Giải quyết:** xác nhận lỗi giảm dưới 2% liên tục 10 phút, sau đó ghi nguyên nhân và hành động khắc phục vào incident log.

## Alert 3 — Answer quality proxy degraded

- **Severity:** warning
- **Duration:** 15 phút liên tục
- **Owner:** LLM Quality On-call
- **SLI/SLO:** guardrail `quality_score_avg >= 0.75`.
- **Điều kiện:** `quality_score_avg < 0.75` trong 15 phút.
- **Ảnh hưởng:** câu trả lời có thể thiếu liên quan hoặc không dùng được cho tác vụ dự kiến. Quality score hiện là proxy heuristic, không phải đánh giá người dùng.
- **Kiểm tra đầu tiên:**
  1. Xem panel quality cùng traffic và retrieval success để loại trừ mẫu quá nhỏ hoặc thiếu retrieval.
  2. Chọn correlation ID có quality thấp và mở trace metadata, prompt version/label, model và token usage.
  3. So sánh prompt candidate/production và xác minh retrieval trả tài liệu phù hợp mà không mở raw PII.
- **Mitigation:** rollback `production` về prompt version ổn định nếu degradation bắt đầu sau lần promote; nếu retrieval success giảm, xử lý corpus/index trước.
- **Giải quyết:** chạy lại cùng bộ câu hỏi đánh giá, xác nhận proxy trở lại ngưỡng và bổ sung review thủ công cho các trường hợp lỗi.

## Error budget

SLO request-based 99.5% trên 28 ngày cho phép 0.5% bad requests: với 1,000 requests thì ngân sách là 5 request. Khi burn rate cao, ưu tiên sửa reliability trước khi promote prompt hoặc phát hành thay đổi có thể tăng lỗi/latency. Budget này tính trên số request, không phải số phút downtime.
