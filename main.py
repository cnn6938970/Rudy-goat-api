from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import zipfile, io
from pdf2image import convert_from_bytes
import fitz
import re

app = FastAPI()

pattern = re.compile(r"F[A-Za-z0-9]\d{3}")

def find_code(text):
    m = pattern.findall(text)
    return m[-1] if m else None

@app.post("/split")
async def split(file: UploadFile = File(...)):
    data = await file.read()

    images = convert_from_bytes(data, dpi=200)
    pdf_doc = fitz.open("pdf", data)

    mem_zip = io.BytesIO()
    z = zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED)

    for i, img in enumerate(images):
        page = pdf_doc.load_page(i)
        text = page.get_text()
        code = find_code(text) or f"page_{i+1:02d}"

        out = io.BytesIO()
        img.save(out, format="PDF")
        z.writestr(f"{code}.pdf", out.getvalue())

    z.close()
    mem_zip.seek(0)
    return StreamingResponse(mem_zip, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=split_output.zip"})
