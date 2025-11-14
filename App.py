from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import tempfile, zipfile, io, os, subprocess, re
from typing import List
from PIL import Image
import pytesseract

app = FastAPI()

# 工號格式：F + 英文/數字 + 3 位數字，例如 FA218、F7A29
CODE_PATTERN = re.compile(r"F[A-Za-z0-9]\d{3}")

def extract_code(text: str):
    """從文字裡抓出最後一個符合 Fxxxx 規則的工號"""
    if not text:
        return None
    matches = CODE_PATTERN.findall(text)
    return matches[-1] if matches else None

def run(cmd):
    """小工具：丟一個外部指令，錯誤就直接丟出"""
    subprocess.run(cmd, check=True)

def pdf_to_pngs(pdf_path: str, out_dir: str):
    """
    用 poppler 的 pdftoppm，把 PDF 每頁轉成 PNG。
    -annot 會把註解層一起 rasterize 進圖片（你 Word 裡加的文字框也會一起被轉進來）
    """
    base = os.path.join(out_dir, "page")
    # -r 300 提高解析度，OCR 比較準
    run(["pdftoppm", "-png", "-r", "300", "-annot", pdf_path, base])

    # 收集輸出的 png 檔
    files = [
        os.path.join(out_dir, f)
        for f in sorted(os.listdir(out_dir))
        if f.startswith("page") and f.endswith(".png")
    ]
    return files

def img_to_pdf_bytes(path: str) -> bytes:
    """把單張圖片轉成單頁 PDF（二進位）"""
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PDF")
    return buf.getvalue()

def ocr_img(path: str):
    """對圖片做 OCR，抓出 Fxxxx 工號"""
    img = Image.open(path)
    text = pytesseract.image_to_string(img, lang="eng")
    return extract_code(text)

@app.post("/split")
async def split(files: List[UploadFile] = File(...)):
    """
    接收多檔案上傳（PDF / JPG / PNG 都可以），
    每一頁 / 每一張圖片做 OCR 找工號，
    用工號命名單頁 PDF，最後打包成 ZIP 回給前端。
    """
    zip_buf = io.BytesIO()

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            file_index = 1

            for f in files:
                ext = os.path.splitext(f.filename)[1].lower()
                raw_path = os.path.join(tmp, f"upload_{file_index}{ext}")

                # 存成暫存檔
                with open(raw_path, "wb") as w:
                    w.write(await f.read())

                # ── PDF：先拆頁 → 每頁轉 PNG → 每頁獨立命名成 PDF ──
                if ext == ".pdf":
                    page_dir = os.path.join(tmp, f"pages_{file_index}")
                    os.makedirs(page_dir, exist_ok=True)

                    png_pages = pdf_to_pngs(raw_path, page_dir)

                    for page_num, png in enumerate(png_pages, start=1):
                        code = ocr_img(png)
                        if not code:
                            code = f"page_{file_index:02d}_{page_num:02d}"

                        pdf_bytes = img_to_pdf_bytes(png)
                        zf.writestr(f"{code}.pdf", pdf_bytes)

                # ── JPG / PNG：直接 OCR 一張 → 輸出成單檔 PDF ──
                else:
                    img = Image.open(raw_path)
                    text = pytesseract.image_to_string(img, lang="eng")
                    code = extract_code(text)
                    if not code:
                        code = f"page_{file_index:02d}"

                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, format="PDF")
                    zf.writestr(f"{code}.pdf", buf.getvalue())

                file_index += 1

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="split_output.zip"'},
    )
