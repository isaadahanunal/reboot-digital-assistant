"""Reboot API + static host.

Runs entirely on localhost. The frontend is a PWA served from ``web/``; the
device agent posts to ``/api/ingest``. Nothing is exposed publicly and no key is
ever sent to the browser.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import aggregate, coach, config, ingest as ingest_mod, prompts, store
from .collector import collector
from .llm import ProviderError, provider_status
from .models import CheckIn, GenerateRequest, IngestPayload, Profile, UsageSession

app = FastAPI(title="Reboot — Digital Well-Being Coach", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    store.init()
    # Measurement should not depend on the user remembering to start it.
    from .collector import autostart_if_enabled
    autostart_if_enabled()


@app.on_event("shutdown")
def _shutdown() -> None:
    collector.stop()


def _err(exc: ProviderError) -> JSONResponse:
    status = {"no_key": 428, "consent": 428, "offline_chat": 428,
              "auth": 401, "rate_limit": 429}.get(exc.kind, 502)
    return JSONResponse(status_code=status,
                        content={"error": str(exc), "kind": exc.kind,
                                 "retryable": exc.retryable})


# --------------------------------------------------------------------- status
@app.get("/api/status")
def status():
    return {
        "ok": True,
        "data": store.counts(),
        "dates": store.available_dates()[:14],
        "today": aggregate.today_key(),
        "provider": provider_status(),
        "profile": coach.load_profile().model_dump(),
    }


# -------------------------------------------------------------------- profile
@app.get("/api/profile")
def get_profile():
    return coach.load_profile().model_dump()


@app.post("/api/profile")
def post_profile(profile: Profile):
    return coach.save_profile(profile).model_dump()


# ------------------------------------------------------------------- settings
@app.get("/api/settings")
def get_settings():
    """Never returns key material -- only whether a key is present."""
    return provider_status()


@app.post("/api/settings")
def post_settings(body: dict):
    allowed = {"provider", "gemini_api_key", "anthropic_api_key",
               "capture_domains", "collector_autostart"}
    patch = {k: v for k, v in body.items() if k in allowed}
    config.save(patch)
    return provider_status()


# --------------------------------------------------------------------- ingest
@app.post("/api/ingest")
def ingest(payload: IngestPayload):
    """Local ingest only. Reboot measures the machine it runs on; the server binds
    to 127.0.0.1 and there is no remote-device path to authorise."""
    accepted = ingest_mod.store_sessions(
        [s.model_dump() for s in payload.sessions], payload.device, payload.source)
    return {"accepted": accepted, "data": store.counts()}


@app.get("/api/collector/status")
def collector_status():
    cfg = config.load()
    return {**collector.status(),
            "autostart": cfg.get("collector_autostart", True),
            "capture_domains": cfg.get("capture_domains", False)}


@app.post("/api/collector/start")
def collector_start(body: dict | None = None):
    body = body or {}
    if "capture_domains" in body:
        config.save({"capture_domains": bool(body["capture_domains"])})
    config.save({"collector_autostart": True})
    return collector.start(config.load().get("capture_domains", False))


@app.post("/api/collector/stop")
def collector_stop():
    config.save({"collector_autostart": False})
    return collector.stop()


# -------------------------------------------------------------------- metrics
@app.get("/api/metrics")
def metrics(date: str | None = Query(default=None)):
    key = date or aggregate.today_key()
    m = aggregate.compute(key)
    return {"metrics": m.model_dump(),
            "discretionary_minutes": aggregate.discretionary_minutes(m),
            "week": aggregate.week_summary(key)}


@app.get("/api/dates")
def dates():
    return {"dates": store.available_dates()}


# ---------------------------------------------------------------------- coach
@app.post("/api/coach/daily")
def coach_daily(req: GenerateRequest, provider: str | None = Query(default=None)):
    try:
        return coach.generate_daily(req.date_key, provider)
    except ProviderError as exc:
        return _err(exc)


@app.post("/api/coach/weekly")
def coach_weekly(req: GenerateRequest, provider: str | None = Query(default=None)):
    try:
        return coach.generate_weekly(req.date_key, provider)
    except ProviderError as exc:
        return _err(exc)


@app.get("/api/coach/latest")
def coach_latest(kind: str = "daily_digest", date: str | None = None):
    art = store.latest_artifact(kind, date)
    if not art:
        raise HTTPException(status_code=404, detail="No generated artifact yet.")
    return art["payload"]


# ----------------------------------------------------------------------- chat
@app.get("/api/chat")
def chat_history():
    return {"messages": store.chat_history(), "context_preview": coach.chat_context()}


@app.post("/api/chat")
def chat_send(body: dict, provider: str | None = Query(default=None)):
    try:
        return coach.chat(body.get("message", ""), provider)
    except ProviderError as exc:
        return _err(exc)


@app.post("/api/chat/clear")
def chat_clear():
    store.clear_chat()
    return {"ok": True, "messages": []}


# ------------------------------------------------------------------- check-in
@app.post("/api/checkin")
def checkin(body: CheckIn):
    store.add_checkin(body.date_key, body.action_id, body.status, body.note)
    return {"ok": True, "checkins": store.recent_checkins()}


@app.get("/api/checkins")
def checkins():
    return {"checkins": store.recent_checkins()}


# -------------------------------------------------------------------- privacy
@app.get("/api/privacy/preview")
def privacy_preview(kind: str = "daily_digest", date: str | None = None):
    return coach.preview_payload(date, kind)


@app.post("/api/privacy/erase")
def privacy_erase():
    store.erase_all()
    return {"ok": True, "data": store.counts()}


@app.get("/api/prompts")
def get_prompts():
    """The app serves its own instructions -- transparency, and the demo's Prompt Lab tab."""
    return {"system": prompts.SYSTEM_COACH, "prompts": prompts.PROMPT_NOTES,
            "schemas": {"daily_digest": prompts.DAILY_DIGEST_SCHEMA,
                        "weekly_plan": prompts.WEEKLY_PLAN_SCHEMA}}


@app.post("/api/demo/seed")
def demo_seed(days: int = 8):
    """Load the reproducible demo week through the ordinary ingest path."""
    import sys
    sys.path.insert(0, str(config.ROOT))
    from agent.demo_seed import build

    sessions = [UsageSession(**row) for row in build(days)]
    return ingest(IngestPayload(device="demo-laptop", source="demo", sessions=sessions))


# --------------------------------------------------------------- api fallback
# Registered after every real route but before the static mount. Without it an
# unknown /api/... POST falls through to StaticFiles, which serves GET/HEAD only
# and answers "405 Method Not Allowed" -- a message that says nothing about the
# actual cause. In practice the cause is almost always a server still running
# older code than the bundle it is serving, so say that.
@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
               include_in_schema=False)
def api_route_missing(rest: str):
    raise HTTPException(
        status_code=404,
        detail=(f"This server has no /api/{rest} route. If Reboot was updated while it was "
                "running, the interface is newer than the server — restart it with ./run.sh."))


# ----------------------------------------------------------------------- web
# Mounted last so every /api route above wins. StaticFiles(html=True) serves
# index.html for "/" and the hashed asset bundle for everything else.
BUILD_HINT = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Reboot — build the UI</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0d0e13;color:#f4f5f8;
font-family:ui-sans-serif,system-ui,sans-serif;padding:24px}div{max-width:520px}h1{font-size:24px;margin:0 0 12px}
p{color:#b6bcc9;line-height:1.6}code{display:block;background:#1e212a;border:1px solid #2c3039;border-radius:10px;
padding:14px;margin:12px 0;font-family:ui-monospace,Menlo,monospace;font-size:13px}</style></head>
<body><div><h1>The interface has not been built yet</h1>
<p>Reboot's frontend is a React app. Build it once, then reload this page:</p>
<code>cd ui &amp;&amp; npm install &amp;&amp; npm run build</code>
<p>The API is already running — <a href="/api/status" style="color:#a396ff">/api/status</a> responds.</p>
</div></body></html>"""


if config.ui_built():
    app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="ui")
else:
    @app.get("/", response_class=HTMLResponse)
    def build_hint():
        return HTMLResponse(BUILD_HINT, status_code=503)
