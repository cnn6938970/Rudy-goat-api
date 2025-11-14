# Rudy-goat-api

後端 API：支援 PDF / JPG / PNG / DOCX → 工號 OCR → 自動分頁命名。

## 🚀 部署到 Render

1. 建一個 GitHub Repo
2. 上傳本資料夾所有檔案
3. Render → New Web Service
4. Environment: **Docker**
5. 點 Deploy

## API

POST /split  
多檔案上傳，回傳 split_output.zip
