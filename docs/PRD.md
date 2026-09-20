# PRODUCT REQUIREMENTS DOCUMENT - PDF2Markdown Pro V2

## 1. Mục tiêu sản phẩm

Chuyển PDF giáo dục tiếng Việt (SGK, SBT, giáo án, tài liệu chuyên môn) thành Markdown có khả năng truy vết, giữ assets, hỗ trợ bảng/công thức và tạo Data Pack. Hệ thống phải ưu tiên **đúng dữ liệu và khả năng kiểm chứng** hơn hình thức.

## 2. Nguyên tắc khóa

- PDF gốc bất biến; luôn giữ SHA-256.
- Không bỏ trang im lặng. Trang không trích được phải `REVIEW`.
- Không dùng LLM làm parser duy nhất.
- Gemini không được tóm tắt/viết lại tự do.
- Auto-fix chỉ là patch tối thiểu, có diff + backup + rollback.
- Không tuyên bố “100% ký tự” nếu chưa có bằng chứng đối chiếu.
- Không để API key trong frontend, log công khai hoặc ZIP.

## 3. Đối tượng sử dụng

- Giáo viên tạo nguồn Markdown từ SGK/SBT.
- Người xây Data Pack cho Gem, NotebookLM, chatbot, RAG.
- Tài liệu tiếng Việt có hình, bảng, sơ đồ, công thức Toán và PDF scan.

## 4. User flow

1. Chọn/kéo thả PDF.
2. Chọn parser và MinerU tier.
3. Chọn OCR: Auto / Off / Force.
4. Chọn Gemini QA: Off / Flagged / All.
5. Tùy chọn Safe Auto-Fix.
6. Nhập metadata Môn/Lớp/Bộ sách.
7. Chạy pipeline.
8. Theo dõi stage/progress.
9. Tải ZIP.
10. Nếu `QA_STATUS=REVIEW`, xem `05_QA/QA_REPORT.md` và trang render tương ứng.

## 5. Pipeline V2

```text
Upload
→ Preflight PDF gốc
→ OCR Preprocessor (optional)
→ Render PDF gốc làm source-of-truth
→ Parser Adapter
   ├─ MinerU 4.x
   └─ PyMuPDF4LLM fallback
→ Rule QA
→ Formula QA
→ Table QA
→ Gemini Visual QA (optional)
→ Safe Auto-Fix (optional)
→ Re-QA / Rollback
→ Data Pack Builder
→ Packager
→ ZIP
```

## 6. OCR Preprocessor

### Auto
Chỉ gọi OCRmyPDF khi preflight thấy ít nhất một trang thiếu text layer. Dùng:
- rotate pages
- deskew
- skip existing text
- ngôn ngữ mặc định `vie+eng`
- output PDF thường, không ép PDF/A

### Force
Dành cho trường hợp PDF text layer hỏng nghiêm trọng; dùng `--force-ocr`. UI phải thể hiện đây là chế độ rủi ro cao hơn.

### Failure
Nếu OCRmyPDF chưa cài hoặc lỗi ở Auto: không crash; dùng PDF gốc và ghi warning. Nếu tài liệu có scan thì QA phải `REVIEW`.

## 7. Parser

### MinerU
- Version: 4.x.
- Tiers: flash/basic/standard/advanced.
- Stateless parse toàn tài liệu.
- Ưu tiên output ZIP để lấy Markdown + structured content + images.

### PyMuPDF4LLM
- Fallback local.
- Page chunks.
- Extract images.
- Chèn `<!-- PAGE: n -->` để kiểm tra coverage.

## 8. Formula Validator

Tối thiểu kiểm tra:
- số delimiter `$` / `$$` không cân bằng;
- ngoặc `{}` trong math block;
- cấu trúc LaTeX rủi ro như `\frac` không có nhóm;
- flag theo trang khi có page chunks.

Không tự sửa công thức bằng heuristic nếu chưa qua Gemini/đối chiếu ảnh.

## 9. Table Validator

Tối thiểu kiểm tra:
- Markdown table header/separator lệch số cột;
- dòng body lệch số cột;
- HTML `<table>` không đóng;
- rowspan/colspan <= 0.

Bảng merge phức tạp ưu tiên HTML + ảnh đối chứng, không ép về Markdown table nếu làm mất cấu trúc.

## 10. Gemini QA

Input mỗi trang:
- ảnh render PDF gốc;
- Markdown ứng viên trang đó.

Output structured JSON:
- page/status/issues;
- evidence;
- original/replacement;
- confidence;
- safe_to_apply.

Không được suy đoán nội dung mờ. `original` phải là substring nguyên văn trong candidate để có khả năng patch.

## 11. Safe Auto-Fix

Chỉ áp dụng khi toàn bộ điều kiện đúng:
- safe_to_apply=true;
- confidence >= threshold;
- error type thuộc whitelist;
- original/replacement khác nhau và không rỗng;
- original xuất hiện đúng một lần trong toàn Markdown;
- patch không quá lớn.

Sau patch:
- chạy lại Rule/Formula/Table QA;
- nếu số broken assets, missing markers, formula/table issue tăng hoặc Markdown giảm bất thường → rollback.
- luôn lưu unified diff và backup.

## 12. Data Pack Builder

Đầu ra:
- `DATA_PACK_MASTER.md`: Markdown hoàn chỉnh + metadata front matter.
- `DATA_PACK_INDEX.json`: heading map, source page nếu có, segment list, source SHA-256.
- `00_INDEX.md`: mục lục điều hướng.
- `chapters/*.md`: phân đoạn theo heading cấp 1/2.

Metadata: subject, grade, book_set. Không tự bịa nếu người dùng không nhập.

## 13. ZIP Contract

- `00_SOURCE/original.pdf`
- `00_SOURCE/ocr_processed.pdf` nếu OCR áp dụng
- `01_MARKDOWN/document.md`
- `02_ASSETS/*`
- `03_PAGE_RENDER/*`
- `04_STRUCTURED/*`
- `05_QA/*`
- `06_DATA_PACK/*`
- `MANIFEST.json`

## 14. Acceptance Criteria

### Source & coverage
- [ ] Original PDF giữ nguyên hash.
- [ ] Page count được lưu trong manifest.
- [ ] Nếu page renders bật: số render = page count.
- [ ] Trang không text không bị bỏ im lặng.

### Security
- [ ] Không lộ API key trong frontend/ZIP.
- [ ] `.env` nằm trong `.gitignore`.

### Parser/OCR
- [ ] Auto fallback hoạt động khi MinerU không có/lỗi.
- [ ] OCR Auto không chạy khi không cần.
- [ ] OCR failure được ghi report.

### QA
- [ ] Formula QA chạy.
- [ ] Table QA chạy.
- [ ] Gemini QA trả structured JSON nếu bật.
- [ ] Safe Auto-Fix sinh diff và rollback khi regression.

### Delivery
- [ ] Data Pack được tạo nếu bật.
- [ ] ZIP mở được và local image refs không hỏng đối với assets đã trích.
- [ ] `python -m compileall app` PASS.
- [ ] Smoke test upload → processing → ZIP PASS.

## 15. Ngoài phạm vi V2

- Không cam kết OCR 100% tuyệt đối.
- Chưa có multi-user/login/cloud billing.
- Chưa có editor web Accept/Reject từng patch theo thao tác người dùng.
- Chưa có batch folder nhiều PDF trong một job.
- Chưa có GPU auto-tuning nâng cao cho từng hãng card.
