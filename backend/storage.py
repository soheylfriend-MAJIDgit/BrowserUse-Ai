"""Persistent JSON storage for LLM profiles, browser settings, templates, and run history."""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"

PROFILES_FILE = DATA_DIR / "profiles.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"

_LOCK = threading.RLock()


DEFAULT_SETTINGS: dict[str, Any] = {
    "headless": False,
    "browser_channel": "auto",  # auto | chrome | msedge | brave | chromium | custom
    "executable_path": "",
    "user_data_dir": "",
    "keep_browser_open": False,
    "window_width": 1280,
    "window_height": 860,
    "use_vision": True,
    "force_persian_output": True,
    "max_steps": 35,
    "max_actions_per_step": 4,
    "flash_mode": False,
    "enable_planning": True,
    "generate_gif": False,
    "custom_instructions": "",
}


TASK_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "shopping_compare",
        "category": "خرید و مقایسه قیمت",
        "icon": "🛍️",
        "title": "مقایسه قیمت و مشخصات کالا در فروشگاه‌ها",
        "description": "جستجوی یک محصول، استخراج قیمت، امتیاز کاربران و لینک خرید در قالب یک لیست مرتب.",
        "prompt": (
            "وارد سایت digikala.com شو، عبارت «هدفون بلوتوثی سامسونگ» را جستجو کن و ۵ محصول اول پرفروش را بازبینی کن. "
            "نام دقیق هر مدل، قیمت فعلی و امتیاز کاربران را در یک جدول مرتب فارسی برایم بنویس و بگو کدام ارزش خرید بیشتری دارد."
        ),
    },
    {
        "id": "news_digest",
        "category": "تحقیق و اخبار",
        "icon": "📰",
        "title": "خلاصه‌سازی داغ‌ترین اخبار تکنولوژی امروز",
        "description": "مراجعه به Hacker News و استخراج و ترجمه ۵ خبر اول به زبان فارسی ساده.",
        "prompt": (
            "به سایت https://news.ycombinator.com برو و ۵ خبر داغ صفحه اول را بخوان. "
            "برای هر خبر: عنوان اصلی، ترجمه و توضیح یک‌خطی به فارسی، تعداد امتیازها و لینک خبر را لیست کن."
        ),
    },
    {
        "id": "data_extraction",
        "category": "استخراج اطلاعات (اسکرپینگ)",
        "icon": "📊",
        "title": "استخراج جدول اطلاعات از یک سایت",
        "description": "جمع‌آوری خودکار لیست قیمت‌ها، کتاب‌ها یا آگهی‌ها بدون نیاز به نوشتن کد اسکرپر.",
        "prompt": (
            "به سایت https://books.toscrape.com برو و از دسته Travel، نام همه کتاب‌های موجود، قیمت پوند و وضعیت موجودی آن‌ها را استخراج کن "
            "و به صورت جدول مرتب نمایش بده."
        ),
    },
    {
        "id": "github_trending",
        "category": "هوش مصنوعی و ابزارها",
        "icon": "⭐",
        "title": "پیدا کردن محبوب‌ترین پروژه‌های هوش مصنوعی امروز در گیت‌هاب",
        "description": "بررسی پروژه‌های ترند روز در GitHub و توضیح کاربرد هر کدام به فارسی.",
        "prompt": (
            "به آدرس https://github.com/trending?since=daily برو و ۶ مخزن (پروژه) اول ترند امروز را بررسی کن. "
            "نام پروژه، زبان برنامه‌نویسی، تعداد ستاره‌های امروز و توضیح کاربرد آن به زبان فارسی ساده را بنویس."
        ),
    },
    {
        "id": "seo_audit",
        "category": "بررسی سایت و سئو",
        "icon": "🔍",
        "title": "تحلیل سریع صفحه اصلی یک وب‌سایت",
        "description": "بررسی عنوان، تیترها، سرعت ظاهری، بخش‌های اصلی و پیشنهاد بهبود برای هر سایت.",
        "prompt": (
            "وارد سایت https://browser-use.com شو، کل صفحه اصلی را اسکرول کن و بگو این سایت چه محصولاتی ارائه می‌دهد، "
            "تعرفه قیمت‌هایش چقدر است و چه مزیت‌هایی نسبت به رقبا اعلام کرده است. نتیجه را به فارسی دسته‌بندی کن."
        ),
    },
    {
        "id": "travel_research",
        "category": "سفر و گردشگری",
        "icon": "✈️",
        "title": "برنامه‌ریزی سفر و بررسی جاهای دیدنی",
        "description": "جستجو در وب برای جمع‌آوری راهنمای کاربردی سفر، هزینه تقریبی و جاذبه‌ها.",
        "prompt": (
            "در گوگل یا ویکی‌سفر درباره «بهترین جاهای دیدنی شیراز در سفر ۳ روزه» جستجو کن، "
            "مکان‌های مهم، ترتیب پیشنهادی بازدید در هر روز و نکات کاربردی را به صورت یک برنامه سفر ۳ روزه فارسی بنویس."
        ),
    },
    {
        "id": "form_test",
        "category": "تست فرم و ورود اطلاعات",
        "icon": "📝",
        "title": "پر کردن خودکار یک فرم آزمایشی در وب",
        "description": "نمونه‌ای برای دیدن نحوه تایپ کردن، انتخاب گزینه و کلیک روی دکمه ثبت توسط ربات.",
        "prompt": (
            "به صفحه فرم آزمایشی https://httpbin.org/forms/post برو، نام مشتری را Ali Rezaei، تلفن را 09120000000، "
            "ایمیل را ali@example.com وارد کن، سایز پیتزا را Medium و یکی از مخلفات را انتخاب کن و در نهایت فرم را ثبت کن و نتیجه برگشتی صفحه را گزارش بده."
        ),
    },
    {
        "id": "bot_check",
        "category": "تست مرورگر و ضدربات",
        "icon": "🛡️",
        "title": "بررسی مشخصات مرورگر و وضعیت تشخیص ربات",
        "description": "بازدید از صفحه تست مرورگر و گزارش وضعیت User-Agent و WebDriver.",
        "prompt": (
            "به سایت https://bot.sannysoft.com برو، صبر کن جدول نتایج کامل بارگذاری شود و سپس گزارش بده کدام بخش‌ها سبز (موفق) "
            "و کدام بخش‌ها قرمز شده‌اند."
        ),
    },
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def mask_api_key(key: str | None) -> str:
    if not key:
        return "بدون کلید"
    k = key.strip()
    if len(k) <= 8:
        return "•" * len(k)
    return f"{k[:5]}••••••••{k[-4:]}"


def _read_json(path: Path, default: Any) -> Any:
    ensure_dirs()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    ensure_dirs()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_profiles_store() -> dict[str, Any]:
    with _LOCK:
        data = _read_json(
            PROFILES_FILE,
            {
                "active_profile_id": None,
                "fallback_profile_id": None,
                "profiles": [],
            },
        )
        if not isinstance(data, dict):
            data = {"active_profile_id": None, "fallback_profile_id": None, "profiles": []}
        data.setdefault("profiles", [])
        data.setdefault("active_profile_id", None)
        data.setdefault("fallback_profile_id", None)
        # Ensure active_profile_id points to an existing profile if any exist
        ids = {p["id"] for p in data["profiles"] if isinstance(p, dict) and "id" in p}
        if data["active_profile_id"] not in ids:
            data["active_profile_id"] = data["profiles"][0]["id"] if data["profiles"] else None
        if data["fallback_profile_id"] not in ids or data["fallback_profile_id"] == data["active_profile_id"]:
            data["fallback_profile_id"] = None
        return data


def save_profiles_store(store: dict[str, Any]) -> None:
    with _LOCK:
        _write_json(PROFILES_FILE, store)


def sanitize_profile_for_client(profile: dict[str, Any]) -> dict[str, Any]:
    out = dict(profile)
    raw_key = out.pop("api_key", "") or ""
    out["has_api_key"] = bool(raw_key.strip())
    out["masked_key"] = mask_api_key(raw_key)
    return out


def get_client_profiles_state() -> dict[str, Any]:
    store = load_profiles_store()
    return {
        "active_profile_id": store["active_profile_id"],
        "fallback_profile_id": store["fallback_profile_id"],
        "profiles": [sanitize_profile_for_client(p) for p in store["profiles"]],
    }


def get_raw_profile(profile_id: str | None) -> dict[str, Any] | None:
    if not profile_id:
        return None
    store = load_profiles_store()
    for p in store["profiles"]:
        if p.get("id") == profile_id:
            return dict(p)
    return None


def get_active_raw_profile() -> dict[str, Any] | None:
    store = load_profiles_store()
    return get_raw_profile(store.get("active_profile_id"))


def get_fallback_raw_profile() -> dict[str, Any] | None:
    store = load_profiles_store()
    fb_id = store.get("fallback_profile_id")
    if fb_id and fb_id != store.get("active_profile_id"):
        return get_raw_profile(fb_id)
    return None


def upsert_profile(payload: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        store = load_profiles_store()
        prof_id = payload.get("id") or f"llm_{uuid.uuid4().hex[:10]}"
        existing = next((p for p in store["profiles"] if p.get("id") == prof_id), None)

        # Preserve existing API key if editing and api_key was not changed (sent empty while keep_existing_key=True)
        incoming_key = payload.get("api_key")
        if existing and incoming_key in (None, "") and payload.get("keep_existing_key", True):
            final_key = existing.get("api_key", "")
        else:
            final_key = (incoming_key or "").strip()

        now_ts = int(time.time())
        record: dict[str, Any] = {
            "id": prof_id,
            "name": (payload.get("name") or "").strip() or f"{payload.get('provider', 'LLM')} - {payload.get('model', '')}",
            "provider": (payload.get("provider") or "google").strip(),
            "model": (payload.get("model") or "").strip(),
            "api_key": final_key,
            "base_url": (payload.get("base_url") or "").strip(),
            "temperature": float(payload.get("temperature", 0.2)),
            "vision_enabled": bool(payload.get("vision_enabled", True)),
            "compat_schema_mode": bool(payload.get("compat_schema_mode", False)),
            "notes": (payload.get("notes") or "").strip(),
            "last_test_ok": existing.get("last_test_ok") if existing else None,
            "last_test_msg": existing.get("last_test_msg", "") if existing else "",
            "updated_at": now_ts,
            "created_at": existing.get("created_at", now_ts) if existing else now_ts,
        }

        if existing:
            idx = store["profiles"].index(existing)
            store["profiles"][idx] = record
        else:
            store["profiles"].append(record)

        if payload.get("set_active", False) or not store["active_profile_id"]:
            store["active_profile_id"] = prof_id

        save_profiles_store(store)
        return sanitize_profile_for_client(record)


def update_profile_test_result(profile_id: str, ok: bool, message: str) -> None:
    with _LOCK:
        store = load_profiles_store()
        for p in store["profiles"]:
            if p.get("id") == profile_id:
                p["last_test_ok"] = ok
                p["last_test_msg"] = message
                p["updated_at"] = int(time.time())
                break
        save_profiles_store(store)


def delete_profile(profile_id: str) -> dict[str, Any]:
    with _LOCK:
        store = load_profiles_store()
        store["profiles"] = [p for p in store["profiles"] if p.get("id") != profile_id]
        if store["active_profile_id"] == profile_id:
            store["active_profile_id"] = store["profiles"][0]["id"] if store["profiles"] else None
        if store["fallback_profile_id"] == profile_id:
            store["fallback_profile_id"] = None
        save_profiles_store(store)
        return get_client_profiles_state()


def set_active_profile(profile_id: str | None, fallback_profile_id: str | None = "__unchanged__") -> dict[str, Any]:
    with _LOCK:
        store = load_profiles_store()
        ids = {p["id"] for p in store["profiles"]}
        if profile_id in ids:
            store["active_profile_id"] = profile_id
        if fallback_profile_id != "__unchanged__":
            if fallback_profile_id in ids and fallback_profile_id != store["active_profile_id"]:
                store["fallback_profile_id"] = fallback_profile_id
            else:
                store["fallback_profile_id"] = None
        if store["fallback_profile_id"] == store["active_profile_id"]:
            store["fallback_profile_id"] = None
        save_profiles_store(store)
        return get_client_profiles_state()


def load_settings() -> dict[str, Any]:
    with _LOCK:
        saved = _read_json(SETTINGS_FILE, {})
        merged = dict(DEFAULT_SETTINGS)
        if isinstance(saved, dict):
            merged.update(saved)
        return merged


def save_settings(new_settings: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        current = load_settings()
        for k in DEFAULT_SETTINGS:
            if k in new_settings:
                current[k] = new_settings[k]
        _write_json(SETTINGS_FILE, current)
        return current


def load_history() -> list[dict[str, Any]]:
    with _LOCK:
        items = _read_json(HISTORY_FILE, [])
        return items if isinstance(items, list) else []


def append_history(entry: dict[str, Any]) -> None:
    with _LOCK:
        items = load_history()
        items.insert(0, entry)
        # Keep most recent 50 runs to keep JSON lightweight
        items = items[:50]
        _write_json(HISTORY_FILE, items)


def clear_history() -> None:
    with _LOCK:
        _write_json(HISTORY_FILE, [])
