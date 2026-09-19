"""Authenticated local FastAPI workbench. Single process/worker only."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .contracts import strict_json
from .control import Controller
from .locking import ServiceLock
from .reports import render
from .service import run_experiment, catalog, KINDS
from .storage import Store


def initialize_data(directory):
    path = Path(directory).resolve()
    path.mkdir(parents=True, exist_ok=True)
    token_file = path/"operator.token"
    if not token_file.exists():
        try:
            fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_urlsafe(32)+"\n")
        except FileExistsError:
            pass
    token = token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("operator token must be at least 32 characters")
    return path, token


def create_app(data_dir=".portal", *, token_override=None, background=True):
    directory, token = initialize_data(data_dir)
    if token_override is not None:
        if len(token_override) < 32:
            raise ValueError("test token too short")
        token = token_override
    store = Store(directory/"portal.sqlite")
    controller = Controller(store)
    semaphore = asyncio.Semaphore(2)
    service_lock = ServiceLock(directory/"service.lock")

    @asynccontextmanager
    async def lifespan(app):
        with service_lock:
            # Dirty shutdown is a lockout, including failure to persist a prior latch.
            if store.get_state("service_dirty", False):
                controller.fault("provenance")
            store.set_state("service_dirty", True, "SERVICE_START")
            if background:
                controller.start_background()
            try:
                yield
            finally:
                controller.shutdown()
                store.set_state("service_dirty", False, "SERVICE_CLEAN_SHUTDOWN")

    app = FastAPI(title="PORTAL TSINDER Research API", version=__version__, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    app.state.store, app.state.controller = store, controller
    security = HTTPBearer(auto_error=False)

    async def authorized(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if credentials is None or not hmac.compare_digest(credentials.credentials, token):
            raise HTTPException(401, "Valid operator Bearer token required")

    async def body(request):
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "application/json required")
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > 1_000_000:
                raise HTTPException(413, "request body exceeds 1 MB")
        try:
            value = strict_json(chunks)
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value
        except (ValueError, UnicodeError) as error:
            raise HTTPException(422, str(error)) from error

    @app.middleware("http")
    async def guards(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
            return Response("Cross-origin requests disabled", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path in ("/", "/assets/app.js", "/assets/style.css"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "mode": "RESEARCH_SIMULATION_ONLY"}

    @app.get("/api/catalog/{name}", dependencies=[Depends(authorized)])
    def get_catalog(name: str):
        try:
            return catalog(name)
        except ValueError as error:
            raise HTTPException(404, str(error)) from error

    @app.get("/api/experiments", dependencies=[Depends(authorized)])
    def kinds():
        return {"kinds": KINDS}

    @app.post("/api/runs", dependencies=[Depends(authorized)])
    async def create_run(request: Request):
        data = await body(request)
        if set(data) != {"kind", "parameters"}:
            raise HTTPException(422, "require exactly kind and parameters")
        try:
            async with semaphore:
                return await run_in_threadpool(run_experiment, store, data["kind"], data["parameters"])
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/api/runs", dependencies=[Depends(authorized)])
    def list_runs():
        return store.runs()

    def get(ident):
        try:
            return store.get_run(ident)
        except KeyError as error:
            raise HTTPException(404, "run not found") from error

    @app.get("/api/runs/{ident}", dependencies=[Depends(authorized)])
    def read_run(ident: str):
        return get(ident)

    @app.get("/api/runs/{ident}/report", response_class=HTMLResponse, dependencies=[Depends(authorized)])
    def report(ident: str):
        return render(get(ident))

    @app.get("/api/runs/{ident}/export", dependencies=[Depends(authorized)])
    def export(ident: str):
        get(ident)
        return Response(store.export(ident), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="portal-run.zip"'})

    @app.get("/api/audit", dependencies=[Depends(authorized)])
    def audit():
        return {"verification": store.verify(), "events": store.events()}

    @app.get("/api/controller", dependencies=[Depends(authorized)])
    def state():
        return controller.snapshot()

    @app.post("/api/controller", dependencies=[Depends(authorized)])
    async def command(request: Request):
        data = await body(request)
        if set(data) - {"action", "value"} or "action" not in data:
            raise HTTPException(422, "require action, optional value")
        try:
            return controller.command(data["action"], data.get("value"))
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/controller/fault", dependencies=[Depends(authorized)])
    async def fault(request: Request):
        data = await body(request)
        if set(data) != {"kind"}:
            raise HTTPException(422, "require fault kind")
        try:
            return controller.fault(data["kind"])
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.post("/api/physical/open", dependencies=[Depends(authorized)])
    def physical():
        raise HTTPException(409, "PHYSICAL_ACTUATOR_UNAVAILABLE: PA-00..PA-11 unresolved; no output issued")

    @app.post("/api/controller/snapshot", dependencies=[Depends(authorized)])
    def snapshot():
        return controller.save_snapshot()

    web = Path(__file__).parent/"web"
    app.mount("/assets", StaticFiles(directory=web), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(web/"index.html")
    return app
