# Output Contract - PDF2Markdown Pro

## Gói ZIP tối thiểu

Bắt buộc:

```text
00_SOURCE/original.pdf
01_MARKDOWN/document.md
02_ASSETS/
04_STRUCTURED/
05_QA/QA_REPORT.md
05_QA/qa_report.json
MANIFEST.json
```

Có điều kiện:

```text
03_PAGE_RENDER/   # khi preserve_page_renders=true
06_DATA_PACK/     # khi build_datapack=true
```

## MANIFEST.json

Nên có tối thiểu:
- `schema_version`
- tên file nguồn
- SHA-256 nguồn
- `source_preserved=true`
- số trang PDF
- parser engine
- OCR mode / trạng thái OCR
- Gemini QA enable/model nếu có
- Safe Auto-Fix enable/status nếu có
- QA status

Không lưu API key, token bí mật hoặc credential.

## Quy tắc Markdown
- Không được âm thầm mất trang.
- Dùng marker trang `<!-- PAGE: n -->` khi pipeline có thể tạo ổn định.
- Link asset phải là đường dẫn tương đối và tồn tại trong ZIP.
- Công thức ưu tiên LaTeX.
- Bảng merge phức tạp có thể dùng HTML hoặc asset đối chứng thay vì ép thành Markdown table sai.

## QA
`qa_report.json` phải là dữ liệu máy đọc được. `QA_REPORT.md` là bản con người đọc được.

Trạng thái:
- `PASS`: không còn critical/high theo rule đang áp dụng.
- `REVIEW`: còn vấn đề cần xem lại.
- `FAILED`: đầu ra không đạt cấu trúc/tính toàn vẹn tối thiểu.
