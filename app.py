from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import tempfile, zipfile, io, os, subprocess, re
from typing import List
from PIL import Image
import pytesseract

app = FastAPI()

CODE_PATTERN = re.compile(r"F[A-Za-z0-9]\d{3}")

def extract_code(t): 
    m = CODE_PATTERN.findall(t or "")
    return m[-1] if m else None

def run(cmd):
    subprocess.run(cmd, check=True)

def pdf_to_pngs(pdf, out):
    base=os.path.join(out,"p")
    run(["pdftoppm","-png","-r","300","-annot",pdf,base])
    return [os.path.join(out,f) for f in sorted(os.listdir(out)) if f.startswith("p")]

def img_to_pdf_bytes(path):
    im=Image.open(path).convert("RGB")
    buf=io.BytesIO()
    im.save(buf,format="PDF")
    return buf.getvalue()

def ocr_img(path):
    text = pytesseract.image_to_string(Image.open(path), lang="eng")
    return extract_code(text)

@app.post("/split")
async def split(files: List[UploadFile] = File(...)):
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            idx = 1
            for f in files:
                ext=os.path.splitext(f.filename)[1].lower()
                raw=os.path.join(tmp,f"u{idx}{ext}")
                with open(raw,"wb") as w:
                    w.write(await f.read())

                if ext==".pdf":
                    od=os.path.join(tmp,f"p{idx}")
                    os.makedirs(od,exist_ok=True)
                    for i,png in enumerate(pdf_to_pngs(raw,od),1):
                        code=ocr_img(png) or f"page_{idx:02d}_{i:02d}"
                        z.writestr(f"{code}.pdf", img_to_pdf_bytes(png))

                else:
                    img=Image.open(raw)
                    text=pytesseract.image_to_string(img,lang="eng")
                    code=extract_code(text) or f"page_{idx:02d}"
                    iobuf=io.BytesIO()
                    img.convert("RGB").save(iobuf,format="PDF")
                    z.writestr(f"{code}.pdf", iobuf.getvalue())

                idx += 1

    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=split.zip"})
