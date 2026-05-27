from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.health import router as health_router
from app.routers.public_data import router as public_data_router
from app.routers.risk import router as risk_router
from app.routers.account import router as account_router


app = FastAPI(
    title="검진AI 리셋코치",
    description="건강검진 기반 만성질환 위험예측 및 퍼스널 개선 플랜 웹앱 MVP",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(public_data_router)
app.include_router(risk_router)
app.include_router(account_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("static/index.html")
