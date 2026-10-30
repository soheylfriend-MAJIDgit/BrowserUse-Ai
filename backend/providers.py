"""LLM Provider Registry, Builder, Tester, and Python Code Generator for Browser Use AI Studio."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "google",
        "name": "Google Gemini (گوگل جمینای)",
        "short_name": "Gemini",
        "badge": "پیشنهادی • سهمیه رایگان",
        "badge_color": "emerald",
        "requires_api_key": True,
        "supports_base_url": False,
        "default_base_url": "",
        "default_model": "gemini-2.5-flash",
        "vision_recommended": True,
        "api_key_placeholder": "AIzaSy...",
        "key_url": "https://aistudio.google.com/apikey",
        "summary_fa": "یکی از بهترین و به‌صرفه‌ترین گزینه‌ها برای کار با مرورگر! گوگل کلید رایگان با سهمیه روزانه عالی ارائه می‌دهد و بینایی (دیدن صفحه وب) فوق‌العاده‌ای دارد.",
        "guide_fa": (
            "۱. وارد سایت aistudio.google.com/apikey شوید و روی دکمه Create API Key کلیک کنید.\n"
            "۲. کلید ساخته‌شده (که با AIza شروع می‌شود) را کپی و در کادر بالا وارد کنید.\n"
            "۳. مدل gemini-2.5-flash سریع، دقیق و دارای سهمیه رایگان است. برای کارهای فوق‌العاده پیچیده از gemini-2.5-pro استفاده کنید.\n"
            "نکته برای کاربران ایران: سرویس گوگل به آی‌پی ایران حساس است؛ هنگام اجرا تحریم‌شکن یا فیلترشکن روشن باشد."
        ),
        "models": [
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (سریع، هوشمند و پیشنهادی)", "vision": True},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (بسیار قدرتمند برای کارهای پیچیده)", "vision": True},
            {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash Lite (بسیار سبک و کم‌مصرف)", "vision": True},
            {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (پایدار و اقتصادی)", "vision": True},
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (دسترسی به ۳۰۰+ مدل با یک کلید)",
        "short_name": "OpenRouter",
        "badge": "محبوب • انواع Llama / GPT / Claude",
        "badge_color": "violet",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.5-flash",
        "vision_recommended": True,
        "api_key_placeholder": "sk-or-v1-...",
        "key_url": "https://openrouter.ai/keys",
        "summary_fa": "با یک کلید OpenRouter می‌توانید بین صدها مدل مختلف (Llama 4، DeepSeek، Gemini، GPT، Claude و Qwen — حتی مدل‌های رایگان :free) جابه‌جا شوید.",
        "guide_fa": (
            "۱. در سایت openrouter.ai ثبت‌نام کرده و از بخش Keys یک کلید جدید (sk-or-v1-...) بسازید.\n"
            "۲. می‌توانید از لیست مدل‌های پیشنهادی انتخاب کنید یا نام دقیق هر مدلی در OpenRouter را در بخش «نام مدل» تایپ کنید (مثلاً meta-llama/llama-4-maverick یا qwen/qwen2.5-vl-72b-instruct:free).\n"
            "۳. اگر مدلی که انتخاب کردید قابلیت دیدن عکس ندارد، تیک «بینایی (Vision)» را خاموش کنید."
        ),
        "models": [
            {"id": "google/gemini-2.5-flash", "label": "Google: Gemini 2.5 Flash (بینایی عالی + ارزان)", "vision": True},
            {"id": "meta-llama/llama-4-maverick", "label": "Meta: Llama 4 Maverick (چندرسانه‌ای و قوی)", "vision": True},
            {"id": "meta-llama/llama-4-scout", "label": "Meta: Llama 4 Scout (سریع و دارای بینایی)", "vision": True},
            {"id": "openai/gpt-4.1-mini", "label": "OpenAI: GPT-4.1 Mini (دقیق و سریع)", "vision": True},
            {"id": "anthropic/claude-sonnet-4", "label": "Anthropic: Claude Sonnet 4 (قدرتمندترین در وب)", "vision": True},
            {"id": "deepseek/deepseek-chat", "label": "DeepSeek V3 Chat (متنی و بسیار ارزان - بدون Vision)", "vision": False},
            {"id": "qwen/qwen-2.5-vl-72b-instruct", "label": "Qwen 2.5 VL 72B (بینایی متن‌باز قوی)", "vision": True},
        ],
    },
    {
        "id": "groq",
        "name": "Groq (اجرای فوق‌سریع مدل‌های Llama و Qwen)",
        "short_name": "Groq (Llama)",
        "badge": "فوق‌سریع • مناسب Llama",
        "badge_color": "amber",
        "requires_api_key": True,
        "supports_base_url": False,
        "default_base_url": "",
        "default_model": "meta-llama/llama-4-maverick-17b-128e-instruct",
        "vision_recommended": True,
        "api_key_placeholder": "gsk_...",
        "key_url": "https://console.groq.com/keys",
        "summary_fa": "اگر به مدل‌های Llama علاقه دارید، Groq سریع‌ترین سرویس دنیا برای اجرای Llama 4 (همراه با بینایی تصویر) است و پلن رایگان روزانه هم دارد!",
        "guide_fa": (
            "۱. وارد console.groq.com/keys شوید و یک کلید (که با gsk_ شروع می‌شود) بسازید.\n"
            "۲. مدل‌های Llama 4 Maverick و Llama 4 Scout در Groq هم فوق‌العاده سریع هستند و هم تصویر صفحه وب را می‌بینند!\n"
            "۳. اگر از مدل‌های صرفاً متنی مثل qwen/qwen3-32b استفاده می‌کنید، گزینه Vision به صورت خودکار یا دستی بهتر است غیرفعال شود."
        ),
        "models": [
            {"id": "meta-llama/llama-4-maverick-17b-128e-instruct", "label": "Llama 4 Maverick 17B (پیشنهادی - دارای بینایی)", "vision": True},
            {"id": "meta-llama/llama-4-scout-17b-16e-instruct", "label": "Llama 4 Scout 17B (فوق‌سریع - دارای بینایی)", "vision": True},
            {"id": "moonshotai/kimi-k2-instruct", "label": "Kimi K2 Instruct (هوشمند برای تحلیل متن وب)", "vision": False},
            {"id": "qwen/qwen3-32b", "label": "Qwen 3 32B (متنی سریع)", "vision": False},
            {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B (مدل بزرگ متن‌باز)", "vision": False},
        ],
    },
    {
        "id": "ollama",
        "name": "Ollama (اجرای لوکال Llama / Qwen روی سیستم خودتان)",
        "short_name": "Ollama (لوکال)",
        "badge": "کاملاً رایگان • بدون API Key",
        "badge_color": "cyan",
        "requires_api_key": False,
        "supports_base_url": True,
        "default_base_url": "http://localhost:11434",
        "default_model": "qwen2.5:14b",
        "vision_recommended": False,
        "api_key_placeholder": "نیازی به کلید ندارد (خالی بگذارید)",
        "key_url": "https://ollama.com/download",
        "summary_fa": "اگر مدل‌های Llama، Qwen یا Gemma را با برنامه Ollama روی کامپیوتر خودتان نصب کرده‌اید، بدون هیچ هزینه و بدون نیاز به API Key از آن‌ها استفاده کنید!",
        "guide_fa": (
            "۱. برنامه Ollama را از ollama.com نصب و اجرا کنید.\n"
            "۲. روی دکمه «شناسایی خودکار مدل‌های نصب‌شده در Ollama» کلیک کنید تا لیست مدل‌های روی کامپیوترتان ظاهر شود.\n"
            "۳. برای وب‌گردی لوکال، مدل‌های حداقل 7B یا 14B (مثل qwen2.5:14b، llama3.1:8b یا qwen2.5vl:7b) نتیجه بهتری می‌دهند."
        ),
        "models": [
            {"id": "qwen2.5:14b", "label": "Qwen 2.5 14B (دقت بالا در خروجی ساختاری)", "vision": False},
            {"id": "qwen2.5:7b", "label": "Qwen 2.5 7B (سبک و مناسب سیستم‌های معمولی)", "vision": False},
            {"id": "llama3.1:8b", "label": "Llama 3.1 8B (مدل محبوب متا)", "vision": False},
            {"id": "llama3.2-vision:11b", "label": "Llama 3.2 Vision 11B (دارای بینایی لوکال)", "vision": True},
            {"id": "gemma3:12b", "label": "Gemma 3 12B (مدل باز گوگل)", "vision": True},
        ],
    },
    {
        "id": "custom_openai",
        "name": "سرویس‌های ایرانی و سفارشی (AvalAI / GapGPT / LM Studio / Proxy)",
        "short_name": "سفارشی / ایرانی",
        "badge": "سازگار با آی‌پی ایران و پروکسی‌ها",
        "badge_color": "rose",
        "requires_api_key": False,
        "supports_base_url": True,
        "default_base_url": "https://api.avalai.ir/v1",
        "default_model": "gpt-4o-mini",
        "vision_recommended": True,
        "api_key_placeholder": "aa-... یا sk-...",
        "key_url": "",
        "summary_fa": "مخصوص اتصال به سرویس‌های واسط ایرانی (مثل AvalAI، GapGPT، MetisAI) یا برنامه‌های لوکال مثل LM Studio و هر سرویسی که استاندارد OpenAI دارد.",
        "guide_fa": (
            "۱. آدرس Base URL سرویس مورد نظر خود را وارد کنید (یا از دکمه‌های آماده زیر کادر آدرس مثل AvalAI، GapGPT یا LM Studio بزنید).\n"
            "۲. کلید API دریافتی از آن سایت و نام دقیق مدل (مثلاً gpt-4o-mini یا gemini-2.5-flash) را وارد کنید.\n"
            "۳. اگر از LM Studio روی سیستم خودتان استفاده می‌کنید، آدرس http://localhost:1234/v1 را انتخاب کنید و کلید را خالی بگذارید."
        ),
        "presets": [
            {"label": "AvalAI (آوال‌آی)", "base_url": "https://api.avalai.ir/v1", "sample_model": "gpt-4o-mini"},
            {"label": "GapGPT (گپ‌جی‌پی‌تی)", "base_url": "https://api.gapgpt.app/v1", "sample_model": "gpt-4o-mini"},
            {"label": "LM Studio (لوکال)", "base_url": "http://localhost:1234/v1", "sample_model": "local-model"},
            {"label": "Together AI", "base_url": "https://api.together.xyz/v1", "sample_model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"},
            {"label": "Fireworks AI", "base_url": "https://api.fireworks.ai/inference/v1", "sample_model": "accounts/fireworks/models/llama4-maverick-instruct-basic"},
        ],
        "models": [
            {"id": "gpt-4o-mini", "label": "gpt-4o-mini (اقتصادی و سریع)", "vision": True},
            {"id": "gpt-4.1-mini", "label": "gpt-4.1-mini (نسل جدید و دقیق)", "vision": True},
            {"id": "gpt-4o", "label": "gpt-4o (قدرتمند همراه با بینایی)", "vision": True},
            {"id": "gemini-2.5-flash", "label": "gemini-2.5-flash (در صورت پشتیبانی سرویس)", "vision": True},
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI (مدل‌های رسمی ChatGPT / GPT-4.1 / GPT-5)",
        "short_name": "OpenAI",
        "badge": "استاندارد طلایی دقت",
        "badge_color": "sky",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "",
        "default_model": "gpt-4.1-mini",
        "vision_recommended": True,
        "api_key_placeholder": "sk-proj-...",
        "key_url": "https://platform.openai.com/api-keys",
        "summary_fa": "سرویس رسمی شرکت OpenAI با بالاترین سازگاری و دقت در کلیک، پر کردن فرم و خواندن صفحات پیچیده وب.",
        "guide_fa": (
            "۱. کلید خود را از platform.openai.com/api-keys دریافت کنید (نیاز به شارژ دلاری دارد).\n"
            "۲. مدل gpt-4.1-mini بهترین تعادل قیمت، سرعت و هوش را برای Browser Use دارد.\n"
            "۳. برای تسک‌های بسیار حساس و چندمرحله‌ای می‌توانید از gpt-4.1 یا gpt-5-mini استفاده کنید."
        ),
        "models": [
            {"id": "gpt-4.1-mini", "label": "GPT-4.1 Mini (بهترین تعادل قیمت و دقت)", "vision": True},
            {"id": "gpt-4.1", "label": "GPT-4.1 (فوق‌العاده دقیق)", "vision": True},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini (ارزان و سریع)", "vision": True},
            {"id": "gpt-4o", "label": "GPT-4o (کلاسیک و قدرتمند)", "vision": True},
            {"id": "gpt-5-mini", "label": "GPT-5 Mini (نسل جدید استدلالی)", "vision": True},
            {"id": "o4-mini", "label": "o4-mini (مدل متفکر برای مسائل سخت)", "vision": True},
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek (دیپ‌سیک رسمی)",
        "short_name": "DeepSeek",
        "badge": "فوق‌العاده ارزان",
        "badge_color": "blue",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "vision_recommended": False,
        "api_key_placeholder": "sk-...",
        "key_url": "https://platform.deepseek.com/api_keys",
        "summary_fa": "مدل بسیار محبوب و ارزان دیپ‌سیک. توجه: مدل deepseek-chat ساختار متنی صفحه (DOM) را تحلیل می‌کند، بنابراین گزینه Vision برای آن به صورت خودکار خاموش می‌شود.",
        "guide_fa": (
            "۱. کلید API را از platform.deepseek.com دریافت کنید.\n"
            "۲. مدل deepseek-chat برای استخراج متن، جستجو و کار با فرم‌ها بسیار اقتصادی است.\n"
            "۳. از آنجا که deepseek-chat ورودی عکس نمی‌گیرد، برنامه به طور هوشمند ساختار کدهای صفحه وب را به آن می‌دهد."
        ),
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek Chat V3 (پیشنهادی - بدون Vision)", "vision": False},
            {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash (سریع)", "vision": False},
            {"id": "deepseek-reasoner", "label": "DeepSeek Reasoner R1 (استدلالی)", "vision": False},
        ],
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude (کلود)",
        "short_name": "Claude",
        "badge": "استاد کار با وب",
        "badge_color": "orange",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "",
        "default_model": "claude-sonnet-4-5",
        "vision_recommended": True,
        "api_key_placeholder": "sk-ant-...",
        "key_url": "https://console.anthropic.com/settings/keys",
        "summary_fa": "مدل‌های Claude Sonnet و Haiku جزو دقیق‌ترین مدل‌های جهان در تشخیص دکمه‌ها و کار با صفحات شلوغ اینترنتی هستند.",
        "guide_fa": (
            "۱. کلید خود را از console.anthropic.com دریافت کنید.\n"
            "۲. مدل claude-haiku-4-5 سریع‌تر و ارزان‌تر است و claude-sonnet-4-5 دقت فوق‌العاده‌ای در کارهای طولانی دارد."
        ),
        "models": [
            {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5 (فوق‌العاده هوشمند)", "vision": True},
            {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (سریع و مقرون‌به‌صرفه)", "vision": True},
            {"id": "claude-opus-4-5", "label": "Claude Opus 4.5 (حداکثر توان استدلال)", "vision": True},
        ],
    },
    {
        "id": "browser_use",
        "name": "Browser Use Cloud (سرویس اختصاصی Browser Use)",
        "short_name": "Browser Use",
        "badge": "اختصاصی مرورگر • اعتبار هدیه",
        "badge_color": "amber",
        "requires_api_key": True,
        "supports_base_url": False,
        "default_base_url": "",
        "default_model": "bu-2-0",
        "vision_recommended": True,
        "api_key_placeholder": "bu_...",
        "key_url": "https://cloud.browser-use.com",
        "summary_fa": "مدل اختصاصی خود تیم سازنده Browser Use (شامل مدل سریع و بهینه‌شده برای وب‌گردی که در سایت رسمی معرفی شده است).",
        "guide_fa": (
            "۱. در cloud.browser-use.com ثبت‌نام کنید (برای حساب‌های واجد شرایط ۱ دلار اعتبار رایگان بدون کارت بانکی می‌دهد).\n"
            "۲. کلید API دریافتی را اینجا وارد کنید تا مستقیم به مدل بهینه‌شده خود Browser Use متصل شوید."
        ),
        "models": [
            {"id": "bu-2-0", "label": "bu-2-0 (مدل اختصاصی پیش‌فرض Browser Use)", "vision": True},
            {"id": "bu-latest", "label": "bu-latest (آخرین نسخه اختصاصی)", "vision": True},
        ],
    },
    {
        "id": "xai",
        "name": "xAI Grok (گروک)",
        "short_name": "xAI Grok",
        "badge": "مدل‌های Grok",
        "badge_color": "slate",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-vision-1212",
        "vision_recommended": True,
        "api_key_placeholder": "xai-...",
        "key_url": "https://console.x.ai/",
        "summary_fa": "اتصال مستقیم به مدل‌های Grok ساخت شرکت xAI با پشتیبانی از بینایی و تحلیل صفحات وب.",
        "guide_fa": "کلید خود را از console.x.ai دریافت کرده و مدل مورد نظر (مانند grok-2-vision-1212 یا grok-3-mini) را انتخاب نمایید.",
        "models": [
            {"id": "grok-2-vision-1212", "label": "Grok 2 Vision (دارای بینایی تصویر)", "vision": True},
            {"id": "grok-3-mini", "label": "Grok 3 Mini (سریع و استدلالی)", "vision": False},
        ],
    },
    {
        "id": "mistral",
        "name": "Mistral AI (میسترال و Pixtral)",
        "short_name": "Mistral",
        "badge": "دارای پلن آزمایشی رایگان",
        "badge_color": "orange",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "https://api.mistral.ai/v1",
        "default_model": "pixtral-large-latest",
        "vision_recommended": True,
        "api_key_placeholder": "...",
        "key_url": "https://console.mistral.ai/api-keys/",
        "summary_fa": "سرویس اروپایی Mistral که در کنسول La Plateforme کلید آزمایشی رایگان ارائه می‌دهد و مدل Pixtral آن قابلیت دیدن صفحات وب را دارد.",
        "guide_fa": "از console.mistral.ai کلید بگیرید. برای داشتن قابلیت دیدن تصویر صفحه وب از مدل pixtral-large-latest یا pixtral-12b-2409 استفاده کنید.",
        "models": [
            {"id": "pixtral-large-latest", "label": "Pixtral Large (بینایی قوی)", "vision": True},
            {"id": "mistral-medium-latest", "label": "Mistral Medium (متعادل)", "vision": True},
            {"id": "mistral-small-latest", "label": "Mistral Small (سریع و سبک)", "vision": True},
        ],
    },
    {
        "id": "cerebras",
        "name": "Cerebras (سرعت فراصوت برای Llama)",
        "short_name": "Cerebras",
        "badge": "سریع‌ترین اجرای متنی Llama",
        "badge_color": "purple",
        "requires_api_key": True,
        "supports_base_url": True,
        "default_base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama-3.3-70b",
        "vision_recommended": False,
        "api_key_placeholder": "csk-...",
        "key_url": "https://cloud.cerebras.ai/",
        "summary_fa": "اجرای مدل‌های Llama و GPT-OSS با سرعت بیش از ۲۰۰۰ توکن بر ثانیه! مناسب کارهای متنی سریع (بدون Vision).",
        "guide_fa": "کلید را از cloud.cerebras.ai بگیرید. چون مدل‌های Cerebras متنی هستند، گزینه Vision بهتر است خاموش باشد.",
        "models": [
            {"id": "llama-3.3-70b", "label": "Llama 3.3 70B (متنی بسیار قوی)", "vision": False},
            {"id": "gpt-oss-120b", "label": "GPT-OSS 120B (بزرگ و سریع)", "vision": False},
        ],
    },
]


PROVIDER_MAP: dict[str, dict[str, Any]] = {p["id"]: p for p in PROVIDERS}


def get_provider_info(provider_id: str) -> dict[str, Any] | None:
    return PROVIDER_MAP.get(provider_id)


def build_llm_from_profile(profile: dict[str, Any]):
    """Instantiate the native browser_use Chat* model from a saved user profile."""
    import browser_use as bu

    provider = profile.get("provider", "google")
    model = (profile.get("model") or "").strip()
    api_key = (profile.get("api_key") or "").strip() or None
    base_url = (profile.get("base_url") or "").strip() or None
    temperature = profile.get("temperature")
    if temperature is not None:
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = None

    p_info = PROVIDER_MAP.get(provider, {})
    if not model:
        model = p_info.get("default_model", "gpt-4o-mini")

    if provider == "google":
        kwargs: dict[str, Any] = {"model": model, "api_key": api_key}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatGoogle(**kwargs)

    if provider == "openrouter":
        kwargs = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://openrouter.ai/api/v1",
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatOpenRouter(**kwargs)

    if provider == "groq":
        kwargs = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatGroq(**kwargs)

    if provider == "ollama":
        host = base_url or "http://localhost:11434"
        ollama_opts = {"temperature": temperature} if temperature is not None else None
        return bu.ChatOllama(model=model, host=host, ollama_options=ollama_opts)

    if provider == "openai":
        kwargs = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatOpenAI(**kwargs)

    if provider in ("custom_openai", "xai"):
        default_url = "https://api.x.ai/v1" if provider == "xai" else "https://api.avalai.ir/v1"
        compat_mode = bool(profile.get("compat_schema_mode", False))
        kwargs = {
            "model": model,
            "api_key": api_key or "not-needed",
            "base_url": base_url or default_url,
            "add_schema_to_system_prompt": compat_mode,
            "dont_force_structured_output": compat_mode,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatOpenAI(**kwargs)

    if provider == "anthropic":
        kwargs = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatAnthropic(**kwargs)

    if provider == "deepseek":
        kwargs = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://api.deepseek.com/v1",
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatDeepSeek(**kwargs)

    if provider == "browser_use":
        kwargs = {"model": model or "bu-2-0", "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return bu.ChatBrowserUse(**kwargs)

    if provider == "mistral":
        kwargs = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://api.mistral.ai/v1",
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatMistral(**kwargs)

    if provider == "cerebras":
        kwargs = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://api.cerebras.ai/v1",
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return bu.ChatCerebras(**kwargs)

    # Fallback to OpenAI-compatible
    return bu.ChatOpenAI(
        model=model,
        api_key=api_key or "not-needed",
        base_url=base_url,
    )


def translate_llm_error_fa(err: Exception | str) -> str:
    """Translate raw SDK/HTTP errors into clear, actionable Persian guidance for non-coders."""
    msg = str(err)
    lower = msg.lower()

    if "401" in lower or "invalid_api_key" in lower or "api key not valid" in lower or "unauthorized" in lower or "authentication" in lower:
        return (
            "❌ کلید API واردشده معتبر نیست (خطای ۴۰۱).\n"
            "لطفاً بررسی کنید که کلید را کامل و بدون فاصله اضافه در ابتدا یا انتها کپی کرده باشید و سرویس انتخابی با نوع کلید یکی باشد."
        )
    if "429" in lower or "quota" in lower or "rate limit" in lower or "insufficient_quota" in lower or "balance" in lower:
        return (
            "⚠️ سهمیه یا شارژ این کلید تمام شده یا به محدودیت تعداد درخواست در دقیقه برخورد کرده است (خطای ۴۲۹).\n"
            "می‌توانید چند لحظه صبر کنید یا از بالای برنامه، کلید/مدل دیگری را انتخاب نمایید."
        )
    if "403" in lower or "user location is not supported" in lower or "permission_denied" in lower or "forbidden" in lower:
        return (
            "🚫 دسترسی از موقعیت جغرافیایی فعلی مسدود است (خطای ۴۰۳).\n"
            "این سرویس (مثلاً گوگل جمینای یا OpenAI) به آی‌پی ایران حساس است. لطفاً تحریم‌شکن یا فیلترشکن خود را روشن کرده و دوباره تست کنید."
        )
    if "404" in lower or "model_not_found" in lower or "not found" in lower or "does not exist" in lower:
        return (
            "🔍 نام مدل یا آدرس Base URL پیدا نشد (خطای ۴۰۴).\n"
            "لطفاً مطمئن شوید نام مدل را دقیق وارد کرده‌اید (یا یکی از مدل‌های پیشنهادی لیست را انتخاب کنید)."
        )
    if "connection" in lower or "connecterror" in lower or "timed out" in lower or "timeout" in lower or "11434" in lower:
        return (
            "🌐 ارتباط با سرور برقرار نشد (خطای شبکه یا تایم‌اوت).\n"
            "اگر از مدل اینترنتی استفاده می‌کنید اتصال اینترنت/فیلترشکن را بررسی کنید، و اگر از Ollama یا LM Studio لوکال استفاده می‌کنید مطمئن شوید برنامه آن روی ویندوز باز و در حال اجراست."
        )
    return f"❌ خطا در ارتباط با مدل: {msg}"


async def test_profile_connection(profile: dict[str, Any]) -> dict[str, Any]:
    """Send a quick ping message to verify an LLM profile works before running browser tasks."""
    from browser_use.llm.messages import UserMessage

    p_info = PROVIDER_MAP.get(profile.get("provider", ""), {})
    if p_info.get("requires_api_key") and not (profile.get("api_key") or "").strip():
        return {
            "ok": False,
            "latency_ms": 0,
            "message_fa": "❌ کلید API وارد نشده است. لطفاً ابتدا کلید این سرویس را وارد نمایید.",
            "raw_error": "Missing API key",
        }

    t0 = time.perf_counter()
    try:
        llm = build_llm_from_profile(profile)
        resp = await llm.ainvoke([UserMessage(content="Reply strictly with the single word: OK")])
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        reply_text = str(getattr(resp, "completion", resp)).strip()[:120]
        return {
            "ok": True,
            "latency_ms": elapsed_ms,
            "reply": reply_text,
            "message_fa": f"✅ اتصال با موفقیت برقرار شد! ({elapsed_ms} میلی‌ثانیه) — پاسخ مدل: {reply_text}",
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": elapsed_ms,
            "message_fa": translate_llm_error_fa(exc),
            "raw_error": str(exc),
        }


async def fetch_ollama_models(host: str = "http://localhost:11434") -> dict[str, Any]:
    """Query local Ollama server for installed Llama/Qwen/Gemma models."""
    clean_host = (host or "http://localhost:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{clean_host}/api/tags")
            r.raise_for_status()
            data = r.json()
            models = []
            for item in data.get("models", []):
                name = item.get("name") or item.get("model")
                size_gb = round((item.get("size") or 0) / (1024 ** 3), 1)
                if name:
                    models.append({"id": name, "size_gb": size_gb})
            return {
                "ok": True,
                "models": models,
                "message_fa": (
                    f"✅ برنامه Ollama فعال است و {len(models)} مدل لوکال پیدا شد."
                    if models
                    else "⚠️ برنامه Ollama روشن است اما هنوز مدلی داخل آن دانلود نشده است (مثلاً دستور ollama pull qwen2.5:7b)."
                ),
            }
    except Exception as exc:
        return {
            "ok": False,
            "models": [],
            "message_fa": "برنامه Ollama روی این آدرس در حال اجرا نیست. اگر می‌خواهید از مدل لوکال استفاده کنید، ابتدا برنامه Ollama را باز کنید.",
            "raw_error": str(exc),
        }


def get_env_vars_for_profile(profile: dict[str, Any] | None) -> dict[str, str]:
    """Return environment variables matching a profile so custom Python scripts can also use it seamlessly."""
    env = dict(os.environ)
    env["ANONYMIZED_TELEMETRY"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"
    if not profile:
        return env

    key = (profile.get("api_key") or "").strip()
    provider = profile.get("provider", "")
    base_url = (profile.get("base_url") or "").strip()
    model = (profile.get("model") or "").strip()

    if model:
        env["BROWSER_USE_ACTIVE_MODEL"] = model
    if provider:
        env["BROWSER_USE_ACTIVE_PROVIDER"] = provider

    if key:
        if provider == "google":
            env["GOOGLE_API_KEY"] = key
            env["GEMINI_API_KEY"] = key
        elif provider == "openrouter":
            env["OPENROUTER_API_KEY"] = key
            env["OPENAI_API_KEY"] = key
        elif provider == "groq":
            env["GROQ_API_KEY"] = key
        elif provider == "openai":
            env["OPENAI_API_KEY"] = key
        elif provider in ("custom_openai", "xai"):
            env["OPENAI_API_KEY"] = key
            env["XAI_API_KEY"] = key
        elif provider == "anthropic":
            env["ANTHROPIC_API_KEY"] = key
        elif provider == "deepseek":
            env["DEEPSEEK_API_KEY"] = key
        elif provider == "browser_use":
            env["BROWSER_USE_API_KEY"] = key
        elif provider == "mistral":
            env["MISTRAL_API_KEY"] = key
        elif provider == "cerebras":
            env["CEREBRAS_API_KEY"] = key

    if base_url and provider in ("custom_openai", "openrouter", "xai", "openai"):
        env["OPENAI_BASE_URL"] = base_url

    return env


def generate_python_code(
    task: str,
    profile: dict[str, Any] | None,
    settings: dict[str, Any],
) -> str:
    """Generate clean, beginner-commented browser-use Python script for the selected task & LLM profile."""
    safe_task = (task or "به سایت news.ycombinator.com برو و ۵ خبر اول را به فارسی خلاصه کن.").replace('"""', "'''")
    provider = (profile or {}).get("provider", "google")
    model = (profile or {}).get("model") or PROVIDER_MAP.get(provider, {}).get("default_model", "gemini-2.5-flash")
    base_url = (profile or {}).get("base_url") or ""
    headless = bool(settings.get("headless", False))
    use_vision = bool(settings.get("use_vision", True))
    max_steps = int(settings.get("max_steps", 40))

    if provider == "google":
        import_line = "from browser_use import Agent, Browser, ChatGoogle"
        llm_init = f'llm = ChatGoogle(model="{model}")  # کلید از پروفایل فعال شما به صورت خودکار تزریق می‌شود'
    elif provider == "openrouter":
        import_line = "from browser_use import Agent, Browser, ChatOpenRouter"
        llm_init = f'llm = ChatOpenRouter(model="{model}")'
    elif provider == "groq":
        import_line = "from browser_use import Agent, Browser, ChatGroq"
        llm_init = f'llm = ChatGroq(model="{model}")'
    elif provider == "ollama":
        host = base_url or "http://localhost:11434"
        import_line = "from browser_use import Agent, Browser, ChatOllama"
        llm_init = f'llm = ChatOllama(model="{model}", host="{host}")'
    elif provider == "anthropic":
        import_line = "from browser_use import Agent, Browser, ChatAnthropic"
        llm_init = f'llm = ChatAnthropic(model="{model}")'
    elif provider == "deepseek":
        import_line = "from browser_use import Agent, Browser, ChatDeepSeek"
        llm_init = f'llm = ChatDeepSeek(model="{model}")'
    elif provider == "browser_use":
        import_line = "from browser_use import Agent, Browser, ChatBrowserUse"
        llm_init = f'llm = ChatBrowserUse(model="{model}")'
    elif provider == "mistral":
        import_line = "from browser_use import Agent, Browser, ChatMistral"
        llm_init = f'llm = ChatMistral(model="{model}")'
    elif provider == "cerebras":
        import_line = "from browser_use import Agent, Browser, ChatCerebras"
        llm_init = f'llm = ChatCerebras(model="{model}")'
    elif provider in ("custom_openai", "xai"):
        url_val = base_url or ("https://api.x.ai/v1" if provider == "xai" else "https://api.avalai.ir/v1")
        import_line = "from browser_use import Agent, Browser, ChatOpenAI"
        llm_init = f'llm = ChatOpenAI(model="{model}", base_url="{url_val}")'
    else:
        import_line = "from browser_use import Agent, Browser, ChatOpenAI"
        llm_init = f'llm = ChatOpenAI(model="{model}")'

    return f'''# کد خودکار ساخته‌شده توسط استودیو Browser Use
# نکته: کلید API انتخابی شما به صورت امن و خودکار هنگام اجرا تزریق می‌شود!

import asyncio
{import_line}


async def main():
    # ۱. تنظیم مدل هوش مصنوعی فعال شما
    {llm_init}

    # ۲. تنظیم مرورگر (headless=False یعنی پنجره مرورگر را جلوی چشمتان باز کند)
    browser = Browser(headless={headless})

    # ۳. تعریف دستور و ساخت ایجنت هوشمند
    agent = Agent(
        task="""{safe_task}""",
        llm=llm,
        browser=browser,
        use_vision={use_vision},
    )

    # ۴. اجرای عملیات و چاپ نتیجه نهایی
    history = await agent.run(max_steps={max_steps})
    print("\\n================ نتیجه نهایی ================")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(main())
'''
