# ANTIGRAVITY MASTER INSTRUCTION - PDF2Markdown Pro V2

Bạn đang phát triển tiếp một dự án đã có kiến trúc và acceptance rõ ràng. KHÔNG viết lại từ đầu nếu chưa chứng minh cần thiết.

## Mục tiêu
Tạo công cụ Windows local-first: PDF → OCR có kiểm soát → parser → Markdown/assets → QA → Safe Auto-Fix → Data Pack → ZIP.

## Quy tắc bất biến
1. Không sửa hoặc ghi đè PDF gốc.
2. Không hard-code API key. Chỉ đọc từ `.env`/secret runtime.
3. Không gửi toàn PDF lên Gemini trong pipeline mặc định; Gemini dùng ảnh trang + candidate Markdown.
4. Không cho AI tóm tắt hoặc tự viết lại tài liệu.
5. Không im lặng bỏ trang, bảng, công thức hoặc hình không đọc được. Flag `REVIEW`.
6. Không bật auto-fix kiểu free-form. Chỉ patch exact substring, unique, whitelist, confidence đủ cao.
7. Mỗi auto-fix phải có before/after diff, backup và regression QA; xấu hơn thì rollback.
8. Giữ tương thích API hiện tại trừ khi có migration rõ ràng.
9. Ưu tiên correctness/traceability trước UI.
10. Không tuyên bố production-ready nếu MinerU/OCR/Gemini live chưa được test trên máy đích.

## Pipeline khóa
Preflight → OCR optional → render original → MinerU/PyMuPDF → Rule QA → Formula QA → Table QA → Gemini QA optional → Safe Auto-Fix optional → Re-QA/Rollback → Data Pack → ZIP.

## Output contract
Giữ các thư mục `00_SOURCE` đến `06_DATA_PACK` và `MANIFEST.json` như PRD V2.

## Tiêu chí bắt buộc trước mỗi lần trả READY
- `python -m compileall app` PASS.
- Unit/smoke tests PASS.
- Không secret trong source.
- Broken local image refs = 0 cho assets đã đóng gói.
- Source hash được giữ.
- Nếu có thay đổi auto-fix: diff tồn tại.
- Nếu QA regression: rollback phải hoạt động.

Đọc `docs/PRD.md` trước khi thêm tính năng.
