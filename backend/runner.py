"""Async Browser Use Agent Runner, Custom Python Runner, and Browser Installer."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from backend.doctor import has_gui_display, resolve_browser_executable
from backend.providers import (
    PROVIDER_MAP,
    build_llm_from_profile,
    get_env_vars_for_profile,
    translate_llm_error_fa,
)
from backend.storage import (
    OUTPUTS_DIR,
    append_history,
    ensure_dirs,
    get_active_raw_profile,
    get_fallback_raw_profile,
    get_raw_profile,
    load_settings,
)

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")


def _format_actions(model_output: Any) -> list[str]:
    actions_desc: list[str] = []
    raw_actions = getattr(model_output, "action", None) or []
    for act in raw_actions:
        try:
            dumped = act.model_dump(exclude_none=True) if hasattr(act, "model_dump") else dict(act)
            for act_name, params in dumped.items():
                if isinstance(params, dict) and params:
                    short_params = ", ".join(f"{k}={repr(v)[:60]}" for k, v in list(params.items())[:3])
                    actions_desc.append(f"{act_name}({short_params})")
                else:
                    actions_desc.append(str(act_name))
        except Exception:
            actions_desc.append(str(act))
    return actions_desc


class AgentRunnerManager:
    """Manages a single active browser-use Agent execution with real-time step & screenshot state."""

    def __init__(self) -> None:
        self.status: str = "idle"  # idle | starting | running | paused | stopping | completed | error | stopped
        self.run_id: str | None = None
        self.task: str = ""
        self.profile_name: str = ""
        self.model_name: str = ""
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.max_steps: int = 35
        self.current_step: int = 0
        self.current_url: str = ""
        self.current_title: str = ""
        self.latest_screenshot: str | None = None
        self.steps: list[dict[str, Any]] = []
        self.logs: list[str] = []
        self.final_result: str | None = None
        self.error_message: str | None = None
        self.gif_url: str | None = None

        self._agent: Any = None
        self._browser: Any = None
        self._asyncio_task: asyncio.Task[Any] | None = None

    def _log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")
        if len(self.logs) > 250:
            self.logs = self.logs[-250:]

    def get_state(self, include_screenshot: bool = True) -> dict[str, Any]:
        elapsed = 0.0
        if self.started_at:
            end_t = self.finished_at or time.time()
            elapsed = round(max(0.0, end_t - self.started_at), 1)
        return {
            "status": self.status,
            "run_id": self.run_id,
            "task": self.task,
            "profile_name": self.profile_name,
            "model_name": self.model_name,
            "elapsed_seconds": elapsed,
            "max_steps": self.max_steps,
            "current_step": self.current_step,
            "current_url": self.current_url,
            "current_title": self.current_title,
            "latest_screenshot": self.latest_screenshot if include_screenshot else None,
            "steps": self.steps,
            "logs": self.logs[-80:],
            "final_result": self.final_result,
            "error_message": self.error_message,
            "gif_url": self.gif_url,
        }

    async def start_run(
        self,
        task: str,
        profile_id: str | None = None,
        override_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.status in ("starting", "running", "paused", "stopping"):
            return {"ok": False, "error": "یک عملیات هم‌اکنون در حال اجراست. ابتدا آن را متوقف کنید."}

        clean_task = (task or "").strip()
        if not clean_task:
            return {"ok": False, "error": "لطفاً ابتدا دستور مورد نظر خود را در کادر بالا بنویسید."}

        profile = get_raw_profile(profile_id) if profile_id else get_active_raw_profile()
        if not profile:
            return {
                "ok": False,
                "error": "هنوز هیچ کلید هوش مصنوعی (API Key) یا مدل لوکالی ثبت نکرده‌اید! از تب «کلیدها و مدل‌ها» یک کلید اضافه کنید.",
            }

        p_info = PROVIDER_MAP.get(profile.get("provider", ""), {})
        if p_info.get("requires_api_key") and not (profile.get("api_key") or "").strip():
            return {
                "ok": False,
                "error": f"پروفایل «{profile.get('name')}» کلید API ندارد. لطفاً کلید آن را در بخش کلیدها وارد کنید.",
            }

        settings = load_settings()
        if override_settings:
            settings.update(override_settings)

        # Reset run state
        self.run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.status = "starting"
        self.task = clean_task
        self.profile_name = profile.get("name", "")
        self.model_name = profile.get("model", "")
        self.started_at = time.time()
        self.finished_at = None
        self.max_steps = max(1, min(200, int(settings.get("max_steps", 35))))
        self.current_step = 0
        self.current_url = ""
        self.current_title = ""
        self.latest_screenshot = None
        self.steps = []
        self.logs = []
        self.final_result = None
        self.error_message = None
        self.gif_url = None

        self._log(f"آماده‌سازی ایجنت با مدل «{self.profile_name}» ({self.model_name})...")
        self._asyncio_task = asyncio.create_task(self._execute_agent(clean_task, profile, settings))
        return {"ok": True, "run_id": self.run_id}

    async def _execute_agent(
        self,
        task: str,
        profile: dict[str, Any],
        settings: dict[str, Any],
    ) -> None:
        import browser_use as bu

        ensure_dirs()
        browser_session = None
        try:
            llm = build_llm_from_profile(profile)
            fallback_profile = get_fallback_raw_profile()
            fallback_llm = None
            if fallback_profile and fallback_profile.get("id") != profile.get("id"):
                try:
                    fallback_llm = build_llm_from_profile(fallback_profile)
                    self._log(f"مدل پشتیبان فعال شد: {fallback_profile.get('name')}")
                except Exception:
                    fallback_llm = None

            # Determine vision support cleanly
            from backend.routeway_llm import KNOWN_TEXT_ONLY_ROUTEWAY_MODELS

            model_lower = (profile.get("model") or "").strip().lower()
            profile_vision = bool(profile.get("vision_enabled", True))
            if model_lower in KNOWN_TEXT_ONLY_ROUTEWAY_MODELS or profile.get("provider") in ("deepseek", "cerebras"):
                profile_vision = False

            want_vision = bool(settings.get("use_vision", True)) and profile_vision
            if settings.get("use_vision", True) and not profile_vision:
                self._log("ℹ️ نکته هوشمند: مدل فعلی متنی است (بدون عکس)؛ تحلیل ساختار صفحه (DOM) خودکار جایگزین شد.")

            # Browser setup
            headless = bool(settings.get("headless", False))
            if not has_gui_display() and not headless:
                headless = True
                self._log("محیط بدون نمایشگر دسکتاپ تشخیص داده شد؛ مرورگر در حالت Headless (مخفی) اجرا می‌شود.")

            channel_choice = settings.get("browser_channel", "auto")
            custom_exe = (settings.get("executable_path") or "").strip()
            resolved_channel, resolved_exe = resolve_browser_executable(channel_choice, custom_exe)

            if resolved_exe:
                self._log(f"مرورگر انتخاب‌شده: {resolved_exe}")
            elif resolved_channel:
                self._log(f"کانال مرورگر انتخاب‌شده: {resolved_channel}")
            else:
                self._log("در حال جستجو یا راه‌اندازی خودکار مرورگر...")

            b_kwargs: dict[str, Any] = {
                "headless": headless,
                "keep_alive": bool(settings.get("keep_browser_open", False)),
                "window_size": {
                    "width": int(settings.get("window_width", 1280)),
                    "height": int(settings.get("window_height", 860)),
                },
            }
            if model_lower.endswith(":free") or profile.get("provider") == "routeway":
                b_kwargs["wait_between_actions"] = 1.4
            if sys.platform.startswith("linux"):
                b_kwargs["chromium_sandbox"] = False
            if resolved_exe:
                b_kwargs["executable_path"] = resolved_exe
            elif resolved_channel:
                b_kwargs["channel"] = resolved_channel

            user_data_dir = (settings.get("user_data_dir") or "").strip()
            if user_data_dir:
                b_kwargs["user_data_dir"] = user_data_dir
                self._log(f"استفاده از پوشه پروفایل کاربری: {user_data_dir}")

            browser_session = bu.Browser(**b_kwargs)
            self._browser = browser_session

            # System prompt extensions
            extra_prompts: list[str] = []
            if settings.get("force_persian_output", True):
                extra_prompts.append(
                    "IMPORTANT: Write your final answer / done result clearly in fluent, well-structured Persian (Farsi) unless the user explicitly asked for another language."
                )
            custom_inst = (settings.get("custom_instructions") or "").strip()
            if custom_inst:
                extra_prompts.append(custom_inst)
            extend_sys = "\n".join(extra_prompts) if extra_prompts else None

            gif_setting: bool | str = False
            gif_filename = f"{self.run_id}.gif"
            if settings.get("generate_gif", False):
                gif_setting = str(OUTPUTS_DIR / gif_filename)

            async def on_new_step(browser_state: Any, model_output: Any, step_num: int) -> None:
                self.current_step = step_num
                url = getattr(browser_state, "url", "") or ""
                title = getattr(browser_state, "title", "") or ""
                screenshot = getattr(browser_state, "screenshot", None)
                if not screenshot and hasattr(browser_state, "get_screenshot"):
                    try:
                        screenshot = browser_state.get_screenshot()
                    except Exception:
                        screenshot = None

                self.current_url = url
                self.current_title = title
                if screenshot:
                    self.latest_screenshot = screenshot

                next_goal = getattr(model_output, "next_goal", "") or ""
                memory = getattr(model_output, "memory", "") or ""
                eval_prev = getattr(model_output, "evaluation_previous_goal", "") or ""
                thinking = getattr(model_output, "thinking", "") or ""
                actions = _format_actions(model_output)

                step_item = {
                    "step": step_num,
                    "time": time.strftime("%H:%M:%S"),
                    "url": url,
                    "title": title,
                    "next_goal": next_goal,
                    "evaluation": eval_prev,
                    "memory": memory,
                    "thinking": thinking,
                    "actions": actions,
                }
                self.steps.append(step_item)
                summary_txt = next_goal or (", ".join(actions) if actions else "اجرای گام")
                self._log(f"گام {step_num}: {summary_txt}")

            agent_kwargs: dict[str, Any] = {
                "task": task,
                "llm": llm,
                "browser": browser_session,
                "use_vision": want_vision,
                "max_actions_per_step": max(1, min(10, int(settings.get("max_actions_per_step", 4)))),
                "flash_mode": bool(settings.get("flash_mode", False)),
                "enable_planning": bool(settings.get("enable_planning", True)),
                "generate_gif": gif_setting,
                "register_new_step_callback": on_new_step,
                "enable_signal_handler": False,
            }
            if extend_sys:
                agent_kwargs["extend_system_message"] = extend_sys
            if fallback_llm is not None:
                agent_kwargs["fallback_llm"] = fallback_llm

            self._agent = bu.Agent(**agent_kwargs)
            self.status = "running"
            self._log("🚀 مرورگر راه‌اندازی شد؛ ربات شروع به کار کرد...")

            history = await self._agent.run(max_steps=self.max_steps)

            # Extract final result & screenshots
            final_text = ""
            try:
                final_text = history.final_result() or ""
            except Exception:
                final_text = ""

            if not final_text:
                try:
                    extracted = history.extracted_content()
                    if extracted:
                        final_text = "\n\n".join(str(x) for x in extracted if x)
                except Exception:
                    pass

            try:
                shots = history.screenshots()
                if shots and shots[-1]:
                    self.latest_screenshot = shots[-1]
            except Exception:
                pass

            if settings.get("generate_gif", False) and (OUTPUTS_DIR / gif_filename).is_file():
                self.gif_url = f"/outputs/{gif_filename}"

            self.finished_at = time.time()
            if self.status == "stopping":
                self.status = "stopped"
                self.final_result = final_text or "عملیات به درخواست شما متوقف شد."
                self._log("⏹️ عملیات توسط کاربر متوقف شد.")
            else:
                self.status = "completed"
                self.final_result = final_text or "عملیات به پایان رسید (خروجی متنی جداگانه‌ای ثبت نشد؛ مراحل بالا را ببینید)."
                self._log("✅ عملیات با موفقیت به پایان رسید!")

            append_history(
                {
                    "id": self.run_id,
                    "timestamp": int(self.finished_at),
                    "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "task": self.task,
                    "profile_name": self.profile_name,
                    "model_name": self.model_name,
                    "status": self.status,
                    "steps_count": len(self.steps),
                    "duration_seconds": round(self.finished_at - (self.started_at or self.finished_at), 1),
                    "final_result": self.final_result,
                    "gif_url": self.gif_url,
                }
            )
        except asyncio.CancelledError:
            self.finished_at = time.time()
            self.status = "stopped"
            self._log("⏹️ اجرای ایجنت لغو شد.")
        except Exception as exc:
            self.finished_at = time.time()
            self.status = "error"
            friendly = translate_llm_error_fa(exc)
            raw_str = str(exc)
            if "no local chrome" in raw_str.lower() or "executable" in raw_str.lower() or "playwright" in raw_str.lower():
                friendly = (
                    "❌ مرورگر کروم یا اج (Microsoft Edge) پیدا نشد یا نتوانست باز شود.\n"
                    "راه‌حل: ۱) اگر از پروفایل شخصی کروم استفاده می‌کنید، ابتدا تمام پنجره‌های باز کروم را ببندید. "
                    "۲) یا از تب «تنظیمات مرورگر» دکمه «نصب خودکار مرورگر Chromium» را بزنید."
                    f"\nجزئیات فنی: {raw_str}"
                )
            self.error_message = friendly
            self._log(f"خطا: {friendly}")
            append_history(
                {
                    "id": self.run_id,
                    "timestamp": int(self.finished_at),
                    "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "task": self.task,
                    "profile_name": self.profile_name,
                    "model_name": self.model_name,
                    "status": "error",
                    "steps_count": len(self.steps),
                    "duration_seconds": round(self.finished_at - (self.started_at or self.finished_at), 1),
                    "final_result": friendly,
                    "gif_url": None,
                }
            )
        finally:
            if browser_session and not settings.get("keep_browser_open", False):
                try:
                    if hasattr(browser_session, "stop"):
                        await browser_session.stop()
                except Exception:
                    pass
            self._agent = None
            self._browser = None

    def pause(self) -> dict[str, Any]:
        if self._agent and self.status == "running":
            self._agent.pause()
            self.status = "paused"
            self._log("⏸️ عملیات موقتاً متوقف شد (می‌توانید در مرورگر مداخله کنید و سپس دکمه ادامه را بزنید).")
            return {"ok": True}
        return {"ok": False, "error": "ایجنت در حال اجرا نیست."}

    def resume(self) -> dict[str, Any]:
        if self._agent and self.status == "paused":
            self._agent.resume()
            self.status = "running"
            self._log("▶️ ادامه عملیات ایجنت...")
            return {"ok": True}
        return {"ok": False, "error": "ایجنت در وضعیت توقف موقت نیست."}

    def stop(self) -> dict[str, Any]:
        if self._agent and self.status in ("starting", "running", "paused"):
            self.status = "stopping"
            self._log("⏹️ درخواست توقف ارسال شد؛ در حال بستن ایمن مرحله فعلی...")
            try:
                self._agent.stop()
            except Exception:
                pass
            if self._asyncio_task and not self._asyncio_task.done():
                # Give agent.stop() a moment, or cancel if still starting
                if self.current_step == 0:
                    self._asyncio_task.cancel()
            return {"ok": True}
        return {"ok": False, "error": "عملیات فعالی وجود ندارد."}

    def add_followup_task(self, new_task: str) -> dict[str, Any]:
        clean = (new_task or "").strip()
        if not clean:
            return {"ok": False, "error": "متن دستور تکمیلی خالی است."}
        if self._agent and self.status in ("running", "paused"):
            self._agent.add_new_task(clean)
            self._log(f"➕ دستور تکمیلی جدید به ربات داده شد: {clean}")
            return {"ok": True}
        return {"ok": False, "error": "ایجنت در حال حاضر فعال نیست."}


class PythonScriptRunner:
    """Runs generated or user-provided Python code inside the active venv with API keys injected."""

    def __init__(self) -> None:
        self.running: bool = False
        self.exit_code: int | None = None
        self.output_lines: list[str] = []
        self._proc: asyncio.subprocess.Process | None = None

    def get_state(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "exit_code": self.exit_code,
            "output": "\n".join(self.output_lines),
        }

    async def start_script(self, code: str, profile_id: str | None = None) -> dict[str, Any]:
        if self.running:
            return {"ok": False, "error": "یک اسکریپت پایتون هم‌اکنون در حال اجراست."}
        if not (code or "").strip():
            return {"ok": False, "error": "کد پایتون خالی است."}

        ensure_dirs()
        script_path = OUTPUTS_DIR / "_user_playground.py"
        script_path.write_text(code, encoding="utf-8")

        profile = get_raw_profile(profile_id) if profile_id else get_active_raw_profile()
        env = get_env_vars_for_profile(profile)

        self.running = True
        self.exit_code = None
        self.output_lines = [
            f">>> اجرای کد پایتون با پروفایل فعال: {(profile or {}).get('name', 'بدون پروفایل')} ...",
            "-" * 60,
        ]
        asyncio.create_task(self._run_subprocess(script_path, env))
        return {"ok": True}

    async def _run_subprocess(self, script_path: Path, env: dict[str, str]) -> None:
        try:
            self._proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(script_path.parent.parent),
                env=env,
            )
            assert self._proc.stdout is not None
            while True:
                line = await self._proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip("\r\n")
                self.output_lines.append(decoded)
                if len(self.output_lines) > 500:
                    self.output_lines = self.output_lines[-500:]
            self.exit_code = await self._proc.wait()
            self.output_lines.append("-" * 60)
            if self.exit_code == 0:
                self.output_lines.append("✅ اجرای کد با موفقیت به پایان رسید (کد خروجی: 0).")
            else:
                self.output_lines.append(f"⚠️ اجرا با کد وضعیت {self.exit_code} خاتمه یافت.")
        except Exception as exc:
            self.exit_code = -1
            self.output_lines.append(f"❌ خطا در اجرای کد پایتون: {exc}")
        finally:
            self.running = False
            self._proc = None

    async def stop_script(self) -> dict[str, Any]:
        if self._proc and self.running:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self.output_lines.append("⏹️ اسکریپت توسط کاربر متوقف شد.")
            return {"ok": True}
        return {"ok": False, "error": "اسکریپتی در حال اجرا نیست."}


class BrowserInstaller:
    """Installs Playwright Chromium from inside the GUI if no Chrome/Edge browser is present."""

    def __init__(self) -> None:
        self.installing: bool = False
        self.logs: list[str] = []
        self.done_ok: bool | None = None

    def get_state(self) -> dict[str, Any]:
        return {
            "installing": self.installing,
            "done_ok": self.done_ok,
            "logs": "\n".join(self.logs),
        }

    async def start_install(self) -> dict[str, Any]:
        if self.installing:
            return {"ok": False, "error": "نصب مرورگر هم‌اکنون در حال انجام است."}
        self.installing = True
        self.done_ok = None
        self.logs = ["⏳ در حال نصب پکیج playwright و دانلود مرورگر Chromium (ممکن است چند دقیقه طول بکشد)..."]
        asyncio.create_task(self._do_install())
        return {"ok": True}

    async def _do_install(self) -> None:
        try:
            for cmd_desc, args in [
                ("نصب ابزار Playwright", [sys.executable, "-m", "pip", "install", "playwright"]),
                ("دانلود مرورگر Chromium", [sys.executable, "-m", "playwright", "install", "chromium"]),
            ]:
                self.logs.append(f"▶ {cmd_desc}...")
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                assert proc.stdout is not None
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    self.logs.append(line.decode("utf-8", errors="replace").rstrip("\r\n"))
                    if len(self.logs) > 200:
                        self.logs = self.logs[-200:]
                rc = await proc.wait()
                if rc != 0:
                    self.done_ok = False
                    self.logs.append(f"❌ خطا در مرحله «{cmd_desc}» (کد {rc}).")
                    return
            self.done_ok = True
            self.logs.append("✅ مرورگر Chromium با موفقیت نصب شد و آماده استفاده است!")
        except Exception as exc:
            self.done_ok = False
            self.logs.append(f"❌ خطا هنگام نصب: {exc}")
        finally:
            self.installing = False


agent_runner = AgentRunnerManager()
script_runner = PythonScriptRunner()
browser_installer = BrowserInstaller()
