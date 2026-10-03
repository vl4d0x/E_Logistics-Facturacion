from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.catalogos.router import router as catalogos_router
from app.modules.servicios.router import router as servicios_router

settings = get_settings()

app = FastAPI(title="Elogistics Facturación API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

api_v1 = "/api/v1"
app.include_router(auth_router, prefix=api_v1)
app.include_router(catalogos_router, prefix=api_v1)
app.include_router(servicios_router, prefix=api_v1)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
