"""FastAPI application serving Browser Use AI Studio UI and REST API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.doctor import get_system_health
from backend.openrouter_llm import fetch_openrouter_free_models
from backend.providers import (
    PROVIDERS,
    fetch_ollama_models,
    generate_python_code,
    test_profile_connection,
)
from backend.routeway_llm import fetch_routeway_free_models
from backend.runner import agent_runner, browser_installer, script_runner
from backend.storage import (
    OUTPUTS_DIR,
    TASK_TEMPLATES,
    bulk_create_openrouter_free_pack,
    bulk_create_routeway_free_pack,
    clear_history,
    delete_profile,
    ensure_dirs,
    get_active_raw_profile,
    get_client_profiles_state,
    get_raw_profile,
    load_history,
    load_settings,
    save_settings,
    set_active_profile,
    update_profile_test_result,
    upsert_profile,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
UI_DIR = ROOT_DIR / "ui"

ensure_dirs()

app = FastAPI(
    title="Browser Use AI Studio",
    description="رابط گرافیکی فارسی و بدون نیاز به کدنویسی برای Browser Use",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfilePayload(BaseModel):
    id: str | None = None
    name: str = ""
    provider: str = "routeway"
    model: str = ""
    api_key: str | None = None
    keep_existing_key: bool = True
    base_url: str = ""
    temperature: float = 0.2
    vision_enabled: bool = True
    free_only: bool = True
    compat_schema_mode: bool = False
    notes: str = ""
    set_active: bool = True


class SwitchProfilePayload(BaseModel):
    active_profile_id: str | None = None
    fallback_profile_id: str | None = "__unchanged__"


class TestProfilePayload(BaseModel):
    profile_id: str | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = 0.2
    free_only: bool = True
    compat_schema_mode: bool = False


class RoutewayBulkPayload(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.routeway.ai/v1"


class OpenRouterBulkPayload(BaseModel):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"


class StartAgentPayload(BaseModel):
    task: str
    profile_id: str | None = None
    override_settings: dict[str, Any] = Field(default_factory=dict)


class FollowupPayload(BaseModel):
    task: str


class GenerateCodePayload(BaseModel):
    task: str = ""
    profile_id: str | None = None


class RunCodePayload(BaseModel):
    code: str
    profile_id: str | None = None


@app.get("/api/bootstrap")
async def api_bootstrap() -> dict[str, Any]:
    return {
        "providers": PROVIDERS,
        "profiles_state": get_client_profiles_state(),
        "settings": load_settings(),
        "templates": TASK_TEMPLATES,
        "system_health": get_system_health(),
        "agent_state": agent_runner.get_state(include_screenshot=True),
        "history": load_history()[:20],
    }


@app.get("/api/system")
async def api_system() -> dict[str, Any]:
    return get_system_health()


@app.post("/api/browser/install")
async def api_browser_install() -> dict[str, Any]:
    return await browser_installer.start_install()


@app.get("/api/browser/install/status")
async def api_browser_install_status() -> dict[str, Any]:
    return browser_installer.get_state()


@app.get("/api/profiles")
async def api_get_profiles() -> dict[str, Any]:
    return get_client_profiles_state()


@app.post("/api/profiles")
async def api_save_profile(payload: ProfilePayload) -> dict[str, Any]:
    saved = upsert_profile(payload.model_dump())
    return {
        "ok": True,
        "profile": saved,
        "profiles_state": get_client_profiles_state(),
    }


@app.delete("/api/profiles/{profile_id}")
async def api_delete_profile(profile_id: str) -> dict[str, Any]:
    state = delete_profile(profile_id)
    return {"ok": True, "profiles_state": state}


@app.post("/api/profiles/switch")
async def api_switch_profile(payload: SwitchProfilePayload) -> dict[str, Any]:
    state = set_active_profile(payload.active_profile_id, payload.fallback_profile_id)
    return {"ok": True, "profiles_state": state}


@app.post("/api/profiles/test")
async def api_test_profile(payload: TestProfilePayload) -> dict[str, Any]:
    if payload.profile_id and not payload.api_key:
        raw = get_raw_profile(payload.profile_id)
        if not raw:
            raise HTTPException(status_code=404, detail="پروفایل پیدا نشد.")
        # Allow overriding model/base_url if user is editing the form without re-entering key
        test_prof = dict(raw)
        if payload.provider:
            test_prof["provider"] = payload.provider
        if payload.model:
            test_prof["model"] = payload.model
        if payload.base_url is not None and payload.base_url != "":
            test_prof["base_url"] = payload.base_url
        test_prof["free_only"] = payload.free_only
    else:
        test_prof = {
            "provider": payload.provider or "routeway",
            "model": payload.model or "",
            "api_key": payload.api_key or "",
            "base_url": payload.base_url or "",
            "temperature": payload.temperature if payload.temperature is not None else 0.2,
            "free_only": payload.free_only,
            "compat_schema_mode": payload.compat_schema_mode,
        }

    result = await test_profile_connection(test_prof)
    if payload.profile_id:
        update_profile_test_result(payload.profile_id, bool(result["ok"]), result["message_fa"])
    result["profiles_state"] = get_client_profiles_state()
    return result


@app.get("/api/routeway/models")
async def api_routeway_models(api_key: str = "", base_url: str = "https://api.routeway.ai/v1") -> dict[str, Any]:
    return await fetch_routeway_free_models(api_key=api_key, base_url=base_url)


@app.post("/api/routeway/bulk-pack")
async def api_routeway_bulk_pack(payload: RoutewayBulkPayload) -> dict[str, Any]:
    try:
        state = bulk_create_routeway_free_pack(api_key=payload.api_key, base_url=payload.base_url)
        return {
            "ok": True,
            "profiles_state": state,
            "message_fa": "✅ ۵ مدل برتر رایگان Routeway (Glimmer 30B، دو مدل Gemma 4 26B، DeepSeek V4 Flash و MiniMax M2.7) به همراه مدل پشتیبان خودکار برایتان ساخته شد!",
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/openrouter/models")
async def api_openrouter_models(api_key: str = "", base_url: str = "https://openrouter.ai/api/v1") -> dict[str, Any]:
    return await fetch_openrouter_free_models(api_key=api_key, base_url=base_url)


@app.post("/api/openrouter/bulk-pack")
async def api_openrouter_bulk_pack(payload: OpenRouterBulkPayload) -> dict[str, Any]:
    try:
        state = bulk_create_openrouter_free_pack(api_key=payload.api_key, base_url=payload.base_url)
        return {
            "ok": True,
            "profiles_state": state,
            "message_fa": "✅ ۵ مدل برتر رایگان OpenRouter (روتر هوشمند، NVIDIA Nemotron 3.5 Super VL، Google Gemma 4 31B، Inkling MoE و Nemotron 550B) به صورت جداگانه در کنار پروفایل‌های شما ذخیره شد!",
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/ollama/models")
async def api_ollama_models(host: str = "http://localhost:11434") -> dict[str, Any]:
    return await fetch_ollama_models(host)


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    return load_settings()


@app.post("/api/settings")
async def api_save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    saved = save_settings(payload)
    return {"ok": True, "settings": saved}


@app.post("/api/agent/start")
async def api_agent_start(payload: StartAgentPayload) -> dict[str, Any]:
    return await agent_runner.start_run(
        task=payload.task,
        profile_id=payload.profile_id,
        override_settings=payload.override_settings,
    )


@app.post("/api/agent/pause")
async def api_agent_pause() -> dict[str, Any]:
    return agent_runner.pause()


@app.post("/api/agent/resume")
async def api_agent_resume() -> dict[str, Any]:
    return agent_runner.resume()


@app.post("/api/agent/stop")
async def api_agent_stop() -> dict[str, Any]:
    return agent_runner.stop()


@app.post("/api/agent/followup")
async def api_agent_followup(payload: FollowupPayload) -> dict[str, Any]:
    return agent_runner.add_followup_task(payload.task)


@app.get("/api/agent/state")
async def api_agent_state(include_screenshot: bool = True) -> dict[str, Any]:
    return agent_runner.get_state(include_screenshot=include_screenshot)


@app.post("/api/code/generate")
async def api_generate_code(payload: GenerateCodePayload) -> dict[str, Any]:
    prof = get_raw_profile(payload.profile_id) if payload.profile_id else get_active_raw_profile()
    settings = load_settings()
    code = generate_python_code(payload.task, prof, settings)
    return {"ok": True, "code": code}


@app.post("/api/code/run")
async def api_run_code(payload: RunCodePayload) -> dict[str, Any]:
    return await script_runner.start_script(payload.code, payload.profile_id)


@app.post("/api/code/stop")
async def api_stop_code() -> dict[str, Any]:
    return await script_runner.stop_script()


@app.get("/api/code/state")
async def api_code_state() -> dict[str, Any]:
    return script_runner.get_state()


@app.get("/api/history")
async def api_get_history() -> dict[str, Any]:
    return {"items": load_history()}


@app.delete("/api/history")
async def api_clear_history() -> dict[str, Any]:
    clear_history()
    return {"ok": True, "items": []}


app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


@app.get("/")
async def serve_index() -> FileResponse:
    index_file = UI_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"error": "فایل رابط کاربری یافت نشد."}, status_code=404)  # type: ignore[return-value]
    return FileResponse(str(index_file))
