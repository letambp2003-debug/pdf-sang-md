# BUILD STATUS - PDF2Markdown Pro V2

## Kết quả build trong môi trường hiện tại

- `python -m compileall app scripts`: **PASS**
- Unit test V2 core (Formula QA / Table QA / Safe Patch / Data Pack): **4/4 PASS**
- Pipeline smoke test với PDF mẫu: **PASS**
  - Preflight: PASS
  - Render page: PASS
  - PyMuPDF fallback extract: PASS
  - Local QA: PASS
  - Data Pack: PASS
  - ZIP packaging: PASS
- FastAPI smoke test: **PASS**
  - POST `/api/jobs`: 200
  - GET job: completed
  - GET download ZIP: 200 `application/zip`
- Secret scan: không phát hiện API key thật; README chỉ chứa placeholder `GEMINI_API_KEY=YOUR_KEY_HERE`.

## Đã nghiệm thu bằng code nhưng chưa có runtime ngoài để test live

- MinerU 4.x model-backed full parse trên Windows đích.
- OCRmyPDF + Tesseract `vie+eng` trên Windows đích.
- Gemini live API với API key thực.

## Trạng thái

**V2 SOURCE PACKAGE READY FOR WINDOWS INTEGRATION TESTING.**

Không tuyên bố OCR/semantic accuracy 100% tuyệt đối. Khi cài trên máy Windows, cần chạy thêm 3 bài test live ở trên trước khi gắn nhãn production-ready.

## V2.1 - Agent / Skill / Frontend
- Root `index.html` created and synced to `app/static/index.html`: PASS
- Inline JavaScript syntax check (`node --check` when available): PASS
- Python compileall after V2.1 changes: PASS
- V2 core unit tests: 4/4 PASS
- `agent.md` created: PASS
- `SKILL.md` created: PASS
- Skill validator: PASS
- Skill package generated as exact `skill.zip`: PASS
- `validate_output_zip.py` smoke test on a valid synthetic bundle: PASS
