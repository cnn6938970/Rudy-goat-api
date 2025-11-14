from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源（含 file://）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
