# PDF2Markdown Pro V2 - Windows / Antigravity

Công cụ local-first: **thả PDF → OCR có kiểm soát → Markdown + assets → QA công thức/bảng → Gemini QA → Safe Auto-Fix có diff/rollback → Data Pack → ZIP**.

## Điểm mới V2

1. **OCR preprocessing tùy chọn** với OCRmyPDF: auto / off / force, xoay trang + deskew, ngôn ngữ mặc định `vie+eng`.
2. **MinerU 4 tier**: flash / basic / standard / advanced. Auto ưu tiên MinerU nếu có, fallback PyMuPDF4LLM.
3. **Formula Validator**: kiểm tra delimiter `$`, `$$`, ngoặc `{}`, một số cấu trúc LaTeX rủi ro.
4. **Table Validator**: kiểm tra bảng Markdown lệch số cột, HTML table không đóng, rowspan/colspan bất hợp lệ.
5. **Gemini QA có scope**: chỉ trang rủi ro để tiết kiệm token hoặc tất cả trang.
6. **Safe Auto-Fix**: chỉ patch lỗi nhỏ có `original` duy nhất, loại lỗi nằm trong whitelist, confidence đạt ngưỡng; lưu diff và tự rollback nếu QA sau sửa xấu hơn.
7. **Data Pack Builder**: sinh `DATA_PACK_MASTER.md`, `00_INDEX.md`, `DATA_PACK_INDEX.json`, và chia segment theo heading để dùng cho Gem / NotebookLM / RAG.
8. **Traceability**: luôn giữ PDF gốc, SHA-256, ảnh render từng trang, QA report, và nếu OCR có chạy thì giữ cả `ocr_processed.pdf`.

## Cài nhanh

Yêu cầu khuyến nghị: Windows 10/11 64-bit, Python 3.12, RAM 16 GB+.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_windows.ps1
```

Mở `http://127.0.0.1:8765`.

## Cài MinerU 4.x (tùy chọn nhưng khuyến nghị)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_mineru_windows.ps1
```

MinerU 4 hỗ trợ Python `>=3.10,<3.15`; Python 3.12 là lựa chọn thực dụng cho môi trường mới. V2 dùng `mineru-kit parse ... --format zip --tier <tier>` để nhận Markdown + structured content + images.

## Cài OCRmyPDF trên Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_ocr_windows.ps1
```

Sau đó kiểm tra:

```powershell
ocrmypdf --version
tesseract --list-langs
```

Muốn OCR tiếng Việt cần thấy `vie` trong danh sách language packs. V2 sử dụng `--output-type pdf` để giảm phụ thuộc vào PDF/A; Ghostscript vẫn có thể cần cho một số workflow ngoài cấu hình mặc định.

## Gemini QA

Copy `.env.example` thành `.env` và điền:

```text
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash
```

Không commit `.env`. API key không được ghi vào frontend hoặc ZIP.

### Hai chế độ QA
- `flagged`: kiểm tra các trang có text rất ít, có ảnh, formula/table issue, trang đầu/cuối. Tiết kiệm token.
- `all`: gửi từng trang + Markdown ứng viên cho Gemini. Phù hợp khi ưu tiên kiểm định toàn bộ hơn chi phí.

## Safe Auto-Fix

Mặc định ngưỡng `0.985`. Patch chỉ được áp dụng nếu:
- Gemini đánh dấu `safe_to_apply=true`.
- `error_type` thuộc whitelist: `wrong_text`, `formula`, `caption`, `heading`.
- `original` tồn tại đúng **một lần** trong Markdown.
- Patch nhỏ, không phải bổ sung đoạn mất, không sửa bảng phức tạp, hình hoặc reading order.
- QA sau patch không tệ hơn QA trước patch.

Mọi lần sửa đều lưu:

```text
05_QA/artifacts/
├── before_autofix.md
├── after_autofix.md
├── autofix.diff
├── autofix_patches.json
└── document_pre_autofix.md   # nếu đã áp dụng patch
```

Nếu QA xấu đi, nội dung được rollback.

## ZIP đầu ra V2

```text
PDF2Markdown_Pro_V2_Result.zip
├── 00_SOURCE/
│   ├── original.pdf
│   └── ocr_processed.pdf        # chỉ khi OCR được áp dụng
├── 01_MARKDOWN/
│   └── document.md
├── 02_ASSETS/
├── 03_PAGE_RENDER/
├── 04_STRUCTURED/
│   ├── structured_content.json  # nếu parser cung cấp
│   ├── preflight.json
│   └── ocr_report.json
├── 05_QA/
│   ├── QA_REPORT.md
│   ├── qa_report.json
│   └── artifacts/
├── 06_DATA_PACK/
│   ├── 00_INDEX.md
│   ├── DATA_PACK_MASTER.md
│   ├── DATA_PACK_INDEX.json
│   └── chapters/
└── MANIFEST.json
```

## Về yêu cầu “100%”

V2 kiểm soát được **100% page coverage, bảo toàn PDF gốc, traceability, asset references và cơ chế flag/QA**. Không nên tuyên bố OCR hoặc semantic accuracy 100% tuyệt đối với mọi PDF scan, công thức khó, bảng merge phức tạp hoặc trang ảnh mờ. Các trường hợp chưa đủ bằng chứng phải để `REVIEW`, không tự suy đoán.

## Kiểm tra môi trường

```powershell
python -m compileall app
python scripts\check_env.py
```

## Antigravity

Mở toàn bộ repo trong Antigravity và dùng `docs/ANTIGRAVITY_MASTER_PROMPT.md` làm instruction đầu tiên. Tiếp tục trên API/acceptance V2, không viết lại từ đầu.

## Bổ sung V2.1 - index.html + Agent + Skill

V2.1 bổ sung lớp giao diện/điều phối để thuận tiện khi mở trong Windows hoặc Antigravity:

```text
index.html                  # frontend standalone; đồng bộ với app/static/index.html
agent.md                    # instruction chính cho agent/Antigravity
gent.md                     # alias dẫn đến agent.md theo tên yêu cầu
SKILL.md                    # entrypoint Skill ở mức project
skill.zip                   # Skill đã validate và package
skill/pdf2markdown-pro/     # source đầy đủ của Skill
```

### Dùng `index.html`
- Khi chạy bằng `run_windows.ps1`, FastAPI phục vụ bản đồng bộ tại `/`.
- Nếu frontend được host riêng trong Antigravity, mở **Cấu hình Antigravity / API server** và đặt API Base URL về backend đang chạy, ví dụ `http://127.0.0.1:8765`.
- Không nhập Gemini API key trong `index.html`; key vẫn chỉ nằm ở `.env` phía server.

### Dùng `agent.md`
Dùng nội dung `agent.md` làm project/system instruction cho agent phát triển hoặc vận hành PDF2Markdown Pro. File này khóa các nguyên tắc: giữ PDF gốc, không bịa, OCR có điều kiện, Gemini chỉ reviewer, Safe Auto-Fix có diff/rollback và trạng thái `PASS/REVIEW/FAILED`.

### Dùng Skill
`skill.zip` là gói Skill độc lập. `SKILL.md` mô tả trigger, workflow, output contract và QA. Skill còn có `scripts/validate_output_zip.py` để kiểm tra một ZIP kết quả trước khi bàn giao.
