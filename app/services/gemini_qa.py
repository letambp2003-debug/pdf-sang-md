import json
from pathlib import Path
from app.models import QAResult


SYSTEM_PROMPT = """Ban la bo kiem dinh PDF sang Markdown cap nghiem ngat.
Muc tieu: phat hien sai lech giua ANH TRANG PDF GOC va MARKDOWN UNG VIEN.
Khong tom tat. Khong viet lai van phong. Khong bo sung kien thuc. Khong suy doan chu khong nhin ro.
Kiem tra: thieu chu, sai chu, thu tu doc, tieu de, bang, cong thuc, chi so tren/duoi, hinh va chu thich.
Neu de xuat sua, truong `original` PHAI la chuoi ton tai NGUYEN VAN trong Markdown ung vien va `replacement` la chuoi thay the nho nhat co the.
Chi dat `safe_to_apply=true` khi:
1) original xuat hien ro rang trong Markdown ung vien;
2) thay the khong lam thay doi y nghia ngoai loi nhin thay;
3) khong lien quan bo sung noi dung bi thieu, thu tu doc, bang phuc tap hoac hinh;
4) confidence >= 0.985.
Neu khong thoa, safe_to_apply=false. Neu khong co loi ro rang, tra PASS.
"""


def qa_page(api_key: str, model: str, page_no: int, image_path: Path, markdown: str) -> dict:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("Chua cai goi google-genai. Chay: python -m pip install google-genai") from exc

    client = genai.Client(api_key=api_key)
    with image_path.open("rb") as f:
        image_part = types.Part.from_bytes(data=f.read(), mime_type="image/png")

    prompt = (
        f"Trang: {page_no}\n\nMARKDOWN UNG VIEN:\n---\n{markdown[:70000]}\n---\n"
        "Doi chieu voi anh trang PDF va tra ve QA co cau truc. Uu tien bang chung cu the, patch toi thieu."
    )
    response = client.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, prompt, image_part],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=QAResult,
        ),
    )
    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        if hasattr(parsed, "model_dump"):
            return parsed.model_dump()
        return parsed
    return json.loads(response.text)
