---
name: pdf2markdown-pro
description: Chuyển đổi PDF, đặc biệt SGK/SBT, giáo án và tài liệu giáo dục tiếng Việt, sang Markdown có giữ hình ảnh, bảng, công thức, nguồn trang và báo cáo QA. Dùng khi cần chuyển PDF sang Markdown, OCR PDF scan, trích xuất assets, kiểm tra công thức/bảng, đối chiếu bằng Gemini, Safe Auto-Fix có diff/rollback, tạo Data Pack cho Gem/NotebookLM/RAG, hoặc kiểm định một gói ZIP PDF2Markdown đã tạo.
---

# PDF2Markdown Pro

## Mục tiêu
Tạo Markdown có thể truy vết về PDF gốc. Ưu tiên bảo toàn dữ liệu và khả năng kiểm chứng hơn việc làm đẹp đầu ra.

## Quy trình
1. Giữ nguyên PDF gốc; tính SHA-256 và đếm trang.
2. Preflight để xác định text layer, trang scan và rủi ro.
3. OCR có điều kiện; mặc định không OCR lại trang đã có text tốt.
4. Render từng trang PDF gốc làm ảnh đối chứng.
5. Trích xuất theo thứ tự MinerU -> PyMuPDF4LLM -> PyMuPDF native fallback.
6. Chuẩn hóa Markdown, assets, công thức và bảng.
7. Chạy rule QA cho coverage, ảnh, formula và table.
8. Nếu bật Gemini, dùng ảnh trang + Markdown ứng viên để phát hiện sai lệch; không cho AI tóm tắt hay viết lại tài liệu.
9. Chỉ áp dụng Safe Auto-Fix khi patch duy nhất, đủ confidence, được đánh dấu an toàn và QA sau sửa không xấu đi; luôn lưu diff và rollback được.
10. Tạo Data Pack khi được yêu cầu và đóng gói ZIP cùng manifest/QA.

## Quy tắc bắt buộc
- Không tuyên bố độ chính xác 100% nếu chưa có kiểm chứng tương ứng.
- Không bỏ trang lỗi hoặc trang rỗng bất thường khỏi báo cáo QA.
- Không tự bịa chữ, số liệu, công thức, chú thích hoặc metadata.
- Không tạo ảnh AI thay thế asset gốc.
- Không làm lộ API key; key chỉ ở server-side environment.
- Không ghi đè PDF gốc.
- Với bảng merge phức tạp, ưu tiên HTML/ảnh đối chứng hơn một bảng Markdown sai.
- Với công thức, ưu tiên LaTeX và đánh `REVIEW` nếu cấu trúc không chắc chắn.

## Đầu ra chuẩn
Gói kết quả nên có:

```text
00_SOURCE/original.pdf
01_MARKDOWN/document.md
02_ASSETS/
03_PAGE_RENDER/
04_STRUCTURED/
05_QA/QA_REPORT.md
05_QA/qa_report.json
06_DATA_PACK/
MANIFEST.json
```

`06_DATA_PACK/` chỉ bắt buộc khi người dùng bật Data Pack. `03_PAGE_RENDER/` có thể bỏ khi người dùng chủ động tắt giữ render.

## QA status
- `PASS`: không còn lỗi critical/high theo bộ kiểm tra đang áp dụng.
- `REVIEW`: còn trang/lỗi cần người xem.
- `FAILED`: pipeline không tạo được đầu ra tối thiểu hoặc mất tính toàn vẹn nguồn.

## Tài liệu đi kèm
Nếu có thư mục `references/`, đọc `references/agent.md` khi cần quy tắc vận hành chi tiết và `references/output_contract.md` khi cần kiểm tra cấu trúc ZIP.

Nếu có `scripts/validate_output_zip.py`, chạy script đó để kiểm định một ZIP kết quả trước khi bàn giao.
