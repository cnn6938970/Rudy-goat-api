from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import zipfile
import re
import io
from pdf2image import convert_from_bytes

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_emp_id(text):
    match = re.search(r"F[A-Z]?\d{3}", text)
    return match.group(0) if match else None

@app.post("/split")
async def split_pdf(file: UploadFile = File(...)):
    pdf_bytes = await file.read()

    images = convert_from_bytes(pdf_bytes)
    zip_buffer = io.BytesIO()
    zipf = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED)

    for i, img in enumerate(images, 1):
        page_bytes = io.BytesIO()
        img.save(page_bytes, format="PNG")
        page_bytes.seek(0)

        text = ""  # 你可以加 OCR
        emp_id = extract_emp_id(text) or f"page_{i:02d}"

        zipf.writestr(f"{emp_id}.png", page_bytes.getvalue())

    zipf.close()
    zip_buffer.seek(0)

    return {
        "status": "ok",
        "message": "split done",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
