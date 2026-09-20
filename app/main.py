import uuid
from pathlib import Path
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.models import JobOptions
from app.services.job_store import JobStore
from app.services.pipeline import process_job
from app.services.ocr_preprocess import ocrmypdf_available
from app.services.extract_mineru import mineru_available


app = FastAPI(title="PDF2Markdown Pro", version="2.1.0")
store = JobStore(settings.data_dir / "jobs")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def home():
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "version": "2.1.0",
        "gemini_configured": bool(settings.gemini_api_key),
        "mineru_available": mineru_available(),
        "ocrmypdf_available": ocrmypdf_available(),
    }


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    mineru_tier: str = Form("standard"),
    ocr_mode: str = Form("auto"),
    ocr_languages: str = Form("vie+eng"),
    gemini_qa: bool = Form(False),
    gemini_qa_scope: str = Form("flagged"),
    auto_apply_safe_fixes: bool = Form(False),
    safe_fix_min_confidence: float = Form(0.985),
    render_dpi: int = Form(240),
    preserve_page_renders: bool = Form(True),
    build_datapack: bool = Form(True),
    subject: str = Form(""),
    grade: str = Form(""),
    book_set: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chi chap nhan tep .pdf")
    if engine not in {"auto", "mineru", "pymupdf"}:
        raise HTTPException(status_code=400, detail="Engine khong hop le")

    try:
        options = JobOptions(
            engine=engine,
            mineru_tier=mineru_tier,
            ocr_mode=ocr_mode,
            ocr_languages=ocr_languages,
            gemini_qa=gemini_qa,
            gemini_qa_scope=gemini_qa_scope,
            auto_apply_safe_fixes=auto_apply_safe_fixes,
            safe_fix_min_confidence=safe_fix_min_confidence,
            render_dpi=render_dpi,
            preserve_page_renders=preserve_page_renders,
            build_datapack=build_datapack,
            subject=subject.strip(),
            grade=grade.strip(),
            book_set=book_set.strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = uuid.uuid4().hex[:16]
    work_dir = store.job_dir(job_id)
    source_pdf = work_dir / "source.pdf"
    size = 0
    with source_pdf.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                out.close()
                source_pdf.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Tep vuot {settings.max_upload_mb} MB")
            out.write(chunk)

    store.create(job_id, file.filename, options.model_dump())
    background_tasks.add_task(process_job, job_id, store)
    return store.read(job_id)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return store.read(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Khong tim thay job")


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str):
    try:
        job = store.read(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Khong tim thay job")
    if job.get("status") != "completed" or not job.get("result_zip"):
        raise HTTPException(status_code=409, detail="Job chua hoan tat")
    path = Path(job["result_zip"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Tep ket qua khong con ton tai")
    return FileResponse(path, media_type="application/zip", filename=f"{job_id}_PDF2Markdown_Pro_V2_1.zip")
