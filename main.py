from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import re
import io
import zipfile

app = FastAPI()

# ======== CORS 解鎖全部來源 =========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 最重要：允許 file:// 來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 工號格式：F + 英文/數字 + 3 數字
ID_PATTERN = re.compile(r"F[A-Za-z0-9]\d{3}")

def find_id_in_image(img: Image.Image):
    text = pytesseract.image_to_string(img, lang="eng")
    matches = ID_PATTERN.findall(text)
    return matches[-1] if matches else None

@app.post("/split")
async def split_pdf(files: list[UploadFile] = File(...)):
    mem_zip = io.BytesIO()
    zipf = zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED)

    for file in files:
        data = await file.read()

        # 轉成圖片（每頁一張）
        pages = convert_from_bytes(data)

        for idx, page_img in enumerate(pages, start=1):

            # OCR 工號
            found_id = find_id_in_image(page_img)
            if not found_id:
                found_id = f"page_{idx:02d}"

            # 儲存為 PDF
            pdf_bytes = io.BytesIO()
            page_img.save(pdf_bytes, format="PDF")
            pdf_bytes.seek(0)

            # 加入 ZIP
            zipf.writestr(f"{found_id}.pdf", pdf_bytes.read())

    zipf.close()
    mem_zip.seek(0)

    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=split_output.zip"},
    )
