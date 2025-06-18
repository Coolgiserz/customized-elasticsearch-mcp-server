from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from .mcp_server import mcp_app
from .middlewares.auth import SimpleAuthMiddleware
from .middlewares.monitor import MonitorMiddleware, metrics
from .middlewares.session import SessionMiddleware
from .config.settings import app_settings
middlewares = [Middleware(SessionMiddleware,
                          secret_key=app_settings.SESSION_SECREY_KEY,
                          max_age=3600),
                Middleware(MonitorMiddleware),
               Middleware(SimpleAuthMiddleware)
               ]

allow_origins = [
    "http://localhost:8000",
]


def create_app():
    app = FastAPI(lifespan=mcp_app.lifespan, middleware=middlewares)
    app.add_middleware(CORSMiddleware,
                       allow_origins=allow_origins,
                       allow_credentials=True,
                       allow_methods=["*"],
                       allow_headers=["*"])
    app.add_route("/metrics", metrics)
    app.mount("/mcp-server", mcp_app)
    return app

app = create_app()


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}



