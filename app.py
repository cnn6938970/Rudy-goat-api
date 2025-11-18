from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io, zipfile, re
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract

app = FastAPI()

# CORS：允許任何前端呼叫
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ID_PATTERN = re.compile(r"F[A-Za-z0-9]\d{3}")

def extract_emp_id(text: str):
    matches = ID_PATTERN.findall(text)
    return matches[-1] if matches else None

@app.post("/split")
async def split_pdf(file: UploadFile = File(...)):
    data = await file.read()

    images = convert_from_bytes(data, dpi=200)

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, img in enumerate(images, start=1):
            ocr_text = pytesseract.image_to_string(img, lang="eng")
            emp_id = extract_emp_id(ocr_text)
            if not emp_id:
                emp_id = f"page_{idx:02d}"

            buf = io.BytesIO()
            img_rgb = img.convert("RGB") if img.mode != "RGB" else img
            img_rgb.save(buf, format="PDF")
            buf.seek(0)

            zf.writestr(f"{emp_id}.pdf", buf.read())

    mem_zip.seek(0)
    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=split_output.zip"}
    )
