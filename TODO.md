# Việc cần hoàn thành — Day 13 Monitoring & LLMOps

Trạng thái cập nhật 2026-09-29. CP3 chính thức đã chạy sau khi Lab Coach mở challenge.

## Đã hoàn thành

- [x] CP0/CP1: correlation ID, enriched structured logs, PII scrubber; baseline 42 records được lưu trước khi chuyển log cũ ra ngoài repo; CP1 validator 100/100 trên 21 log mới.
- [x] Test: 27 passed với pytest temp directory riêng. CP4 output mới tại `submission/evidence/01-pytest.txt`.
- [x] CP2 tracing: root `lab-agent-run` có child `retriever` và `fake-llm-generation`; generation có model, prompt link, token usage và cost; 10 trace mới được kiểm tra, raw input/output không được capture.
- [x] CP2 prompt versioning: `day13-chat` v1 (`baseline`, `production`) và v2 (`candidate`); đã promote production lên v2 rồi rollback v1. Trạng thái cuối production v1.
- [x] CP2 dashboard: `dashboard.py` có 6 panel trên log thật, rolling window 60 phút, đơn vị và threshold/SLO lines; `validate_dashboard.py` 6/6.
- [x] CP2 SLO/alerts: `config/slo.yaml`, `config/alert_rules.yaml` và `docs/alerts.md` đã hoàn thiện; channel trong YAML cần nối với hệ thống alert thật nếu triển khai.
- [x] Evidence text cho validators, pytest, structured log, PII redaction, prompt versions/rollback, waterfall/metadata và dashboard runtime đã lưu trong `submission/evidence/`.
- [x] Practice `rag_slow` đã tắt; metric/log/trace practice được lưu riêng, không coi là incident challenge.
- [x] CP3: challenge ID K4-L3A đã xác nhận; 5/5 request chạy với concurrency 5; metric, log/correlation ID và trace waterfall đối chiếu cùng một incident; incident đã tắt sau workload.
- [x] CP3 evidence: `submission/evidence/12-incident-metric.txt`, `13-incident-log.txt`, `14-incident-trace.txt`; log validator sau workload 100/100, 0 PII leak.

## Còn lại

### CP4 — Chốt bài nộp

- [x] Lưu PNG runtime dashboard vào `submission/evidence/11-dashboard-overview.png`.
- [x] Evidence Langfuse cho trace list/waterfall/metadata và prompt versions/rollback đã lưu dạng output text từ project cá nhân; chưa có screenshot giao diện.
- [x] Report/evidence incident chính thức khớp challenge ID, metric, correlation ID và trace ID.
- [x] Tests và validators cuối đã chạy; còn kiểm tra status sau khi commit.
- [x] Report dẫn tới lịch sử commit cuối; lấy SHA chính xác từ `git log -1 --format=%H` để nộp trên LMS.
- [x] Commit/push source, report và evidence cá nhân; `.env`, `.venv`, logs riêng tư và challenge files bị ignore.

## Kết quả kiểm tra gần nhất

- `validate_logs.py`: sau challenge 100/100 trên 115 records, 56 correlation IDs, 0 lỗi field/enrichment, 0 PII leak.
- `validate_dashboard.py`: hợp lệ 6/6 panel.
- `pytest`: 27 passed, một cảnh báo deprecation từ Starlette.
- `.env` vẫn đặt `LANGFUSE_PROMPT_LABEL=production`; label cuối trong Langfuse trỏ tới v1.
- Dashboard runtime screenshot đã được lưu tại `submission/evidence/11-dashboard-overview.png`.
