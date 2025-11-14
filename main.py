from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io, zipfile
from pdf2image import convert_from_bytes
import pytesseract
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pattern = re.compile(r"F[A-Z0-9][0-9]{3}")

@app.post("/split")
async def split(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    images = convert_from_bytes(pdf_bytes)

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w") as z:
        for idx, img in enumerate(images):
            text = pytesseract.image_to_string(img)
            match = pattern.search(text)
            name = match.group() if match else f"page_{idx+1}"
            buf = io.BytesIO()
            img.save(buf, format="PDF")
            z.writestr(f"{name}.pdf", buf.getvalue())

    mem_zip.seek(0)
    return StreamingResponse(mem_zip, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=split_output.zip"})