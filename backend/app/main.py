from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router
from app.tracks.router import router as tracks_router
from app.progress.router import router as progress_router
from app.quiz.router import router as quiz_router

app = FastAPI(title="Lernr API")

app.include_router(auth_router)
app.include_router(tracks_router)
app.include_router(progress_router)
app.include_router(quiz_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}