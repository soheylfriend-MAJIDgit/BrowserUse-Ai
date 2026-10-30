"""Dedicated Routeway AI (https://api.routeway.ai/v1) LLM adapter optimized for Free (:free) models."""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, TypeVar, overload

import httpx
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel

from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.openai.serializer import OpenAIMessageSerializer
from browser_use.llm.schema import SchemaOptimizer
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage

T = TypeVar("T", bound=BaseModel)

ROUTEWAY_BASE_URL = "https://api.routeway.ai/v1"

# Cache preferred structured-output strategy per model ID so we don't waste Routeway's 20 RPM free limit:
# Values: "json_schema" | "tools" | "prompt_json"
_MODEL_STRATEGY_CACHE: dict[str, str] = {
    # Known models without response_format in supported_parameters:
    "deepseek-v4-flash:free": "tools",
    "minimax-m2.7:free": "tools",
    "step-3.5-flash:free": "prompt_json",
}

# Known non-vision free models on Routeway (auto-disables screenshot input even if user left Vision checked)
KNOWN_TEXT_ONLY_ROUTEWAY_MODELS: set[str] = {
    "deepseek-v4-flash:free",
    "minimax-m2.7:free",
    "ling-3.0-flash:free",
    "ling-2.6-flash:free",
    "step-3.5-flash:free",
    "nemotron-nano-9b-v2:free",
    "deepseek-r1:free",
    "deepseek-r1t-chimera:free",
    "deepseek-v3.1:free",
    "deepseek-v3-0324:free",
    "llama-3.3-70b-instruct:free",
    "mistral-nemo-instruct:free",
    "mistral-small-3:free",
}


def strip_reasoning_and_extract_json(raw_text: str) -> str:
    """Strip <think>...</think> reasoning traces and ```json fences, returning clean JSON text."""
    text = (raw_text or "").strip()
    # Remove <think>...</think> blocks produced by reasoning models
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    # If an unclosed <think> precedes a JSON block, strip up to </think> if present
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()

    # Extract fenced ```json ... ``` block if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()
        if candidate.startswith("{"):
            return candidate

    # Otherwise extract outermost {...} JSON object
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]
    return text


def ensure_routeway_free_model_id(model: str, free_only: bool = True) -> str:
    """Ensure model ID uses :free when free_only guard is enabled."""
    clean = (model or "").strip()
    if not clean:
        return "muse-glimmer-30b:free"
    if free_only and not clean.endswith(":free"):
        raise ModelProviderError(
            message=(
                f"قفل «فقط مدل‌های رایگان Routeway» فعال است اما مدل «{clean}» پسوند :free ندارد! "
                f"لطفاً یکی از مدل‌های رایگان (که انتهای نامشان :free دارد مثل {clean}:free) را انتخاب کنید."
            ),
            status_code=400,
            model=clean,
        )
    return clean


@dataclass
class ChatRouteway(BaseChatModel):
    """
    Adaptive OpenAI-compatible wrapper for Routeway AI (https://api.routeway.ai/v1),
    specifically tuned for Routeway's Free (:free) models (Glimmer 30B, Gemma 4 26B,
    DeepSeek V4 Flash, MiniMax M2.7, etc.).
    """

    model: str = "muse-glimmer-30b:free"
    api_key: str | None = None
    base_url: str = ROUTEWAY_BASE_URL
    temperature: float | None = 0.2
    free_only: bool = True
    timeout: float = 120.0
    max_retries: int = 2
    _extra_skip_temp: set[str] = field(default_factory=lambda: {"minimax-m2.7:free"})

    @property
    def provider(self) -> str:
        return "routeway"

    @property
    def name(self) -> str:
        return str(self.model)

    def _get_client(self) -> AsyncOpenAI:
        key = (self.api_key or os.getenv("ROUTEWAY_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        if not key:
            raise ModelProviderError(
                message="کلید API سایت Routeway وارد نشده است.",
                status_code=401,
                model=self.name,
            )
        return AsyncOpenAI(
            api_key=key,
            base_url=(self.base_url or ROUTEWAY_BASE_URL).rstrip("/"),
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    @staticmethod
    def _extract_usage(response: Any) -> ChatInvokeUsage | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(prompt_details, "cached_tokens", None) if prompt_details else None
        return ChatInvokeUsage(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            prompt_cached_tokens=cached,
            prompt_cache_creation_tokens=None,
            prompt_image_tokens=None,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )

    def _base_params(self, model_id: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.temperature is not None and model_id not in self._extra_skip_temp:
            params["temperature"] = self.temperature
        return params

    async def _call_with_transient_retry(self, coro_factory):
        """Retry transient 502/503/504 upstream errors common on free model pools."""
        delays = [2.0, 4.5]
        last_exc: Exception | None = None
        for attempt in range(len(delays) + 1):
            try:
                return await coro_factory()
            except RateLimitError as exc:
                raise ModelRateLimitError(message=str(exc), model=self.name) from exc
            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code in (502, 503, 504) and attempt < len(delays):
                    await asyncio.sleep(delays[attempt])
                    continue
                raise
            except APIConnectionError as exc:
                last_exc = exc
                if attempt < len(delays):
                    await asyncio.sleep(delays[attempt])
                    continue
                raise
        if last_exc:
            raise last_exc

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        model_id = ensure_routeway_free_model_id(self.model, free_only=self.free_only)
        client = self._get_client()
        serialized = OpenAIMessageSerializer.serialize_messages(messages)

        try:
            # 1) Plain text invocation (e.g., API key connection test)
            if output_format is None:
                params = self._base_params(model_id)
                try:
                    resp = await self._call_with_transient_retry(
                        lambda: client.chat.completions.create(
                            model=model_id,
                            messages=serialized,
                            **params,
                        )
                    )
                except APIStatusError as exc:
                    if exc.status_code == 400 and "temperature" in str(exc).lower():
                        self._extra_skip_temp.add(model_id)
                        resp = await self._call_with_transient_retry(
                            lambda: client.chat.completions.create(
                                model=model_id,
                                messages=serialized,
                            )
                        )
                    else:
                        raise

                content = ""
                if resp.choices and resp.choices[0].message:
                    content = resp.choices[0].message.content or ""
                # Strip <think> if model only returned reasoning + answer
                clean_txt = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip() or content
                return ChatInvokeCompletion(
                    completion=clean_txt,
                    usage=self._extract_usage(resp),
                    stop_reason=resp.choices[0].finish_reason if resp.choices else None,
                )

            # 2) Structured Pydantic output required by browser-use Agent
            optimized_schema = SchemaOptimizer.create_optimized_json_schema(
                output_format,
                remove_min_items=True,
                remove_defaults=True,
            )

            preferred = _MODEL_STRATEGY_CACHE.get(model_id, "json_schema")
            strategies_order = [preferred] + [
                s for s in ("json_schema", "tools", "prompt_json") if s != preferred
            ]

            last_err: Exception | None = None
            for strategy in strategies_order:
                try:
                    result = await self._try_structured_strategy(
                        client=client,
                        model_id=model_id,
                        serialized_messages=serialized,
                        output_format=output_format,
                        optimized_schema=optimized_schema,
                        strategy=strategy,
                    )
                    _MODEL_STRATEGY_CACHE[model_id] = strategy
                    return result
                except (ModelRateLimitError, RateLimitError) as rl_exc:
                    raise ModelRateLimitError(message=str(rl_exc), model=self.name) from rl_exc
                except APIStatusError as api_exc:
                    if api_exc.status_code in (401, 402, 403):
                        raise ModelProviderError(
                            message=api_exc.message,
                            status_code=api_exc.status_code,
                            model=self.name,
                        ) from api_exc
                    last_err = api_exc
                    continue
                except Exception as exc:
                    last_err = exc
                    continue

            raise ModelProviderError(
                message=f"خطا در دریافت خروجی ساختاری از مدل رایگان {model_id}: {last_err}",
                status_code=500,
                model=self.name,
            )

        except (ModelProviderError, ModelRateLimitError):
            raise
        except RateLimitError as exc:
            raise ModelRateLimitError(message=exc.message, model=self.name) from exc
        except APIStatusError as exc:
            raise ModelProviderError(message=exc.message, status_code=exc.status_code, model=self.name) from exc
        except Exception as exc:
            raise ModelProviderError(message=str(exc), model=self.name) from exc

    async def _try_structured_strategy(
        self,
        client: AsyncOpenAI,
        model_id: str,
        serialized_messages: list[Any],
        output_format: type[T],
        optimized_schema: dict[str, Any],
        strategy: str,
    ) -> ChatInvokeCompletion[T]:
        params = self._base_params(model_id)

        if strategy == "json_schema":
            resp = await self._call_with_transient_retry(
                lambda: client.chat.completions.create(
                    model=model_id,
                    messages=serialized_messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "agent_output",
                            "strict": True,
                            "schema": optimized_schema,
                        },
                    },  # type: ignore[arg-type]
                    **params,
                )
            )
            raw_content = (resp.choices[0].message.content or "") if resp.choices else ""
            cleaned = strip_reasoning_and_extract_json(raw_content)
            parsed = output_format.model_validate_json(cleaned)
            return ChatInvokeCompletion(
                completion=parsed,
                usage=self._extract_usage(resp),
                stop_reason=resp.choices[0].finish_reason if resp.choices else None,
            )

        if strategy == "tools":
            tool_schema = dict(optimized_schema)
            tool_schema.pop("title", None)
            tool_name = output_format.__name__
            tools_param = [
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Return structured output matching {tool_name}",
                        "parameters": tool_schema,
                    },
                }
            ]
            resp = await self._call_with_transient_retry(
                lambda: client.chat.completions.create(
                    model=model_id,
                    messages=serialized_messages,
                    tools=tools_param,  # type: ignore[arg-type]
                    tool_choice={"type": "function", "function": {"name": tool_name}},  # type: ignore[arg-type]
                    **params,
                )
            )
            msg = resp.choices[0].message if resp.choices else None
            if msg and msg.tool_calls:
                raw_args = msg.tool_calls[0].function.arguments
                data = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                parsed = output_format.model_validate(data)
                return ChatInvokeCompletion(
                    completion=parsed,
                    usage=self._extract_usage(resp),
                    stop_reason=resp.choices[0].finish_reason if resp.choices else None,
                )
            # Some models ignore tool_choice and emit JSON in message.content anyway
            if msg and msg.content:
                cleaned = strip_reasoning_and_extract_json(msg.content)
                parsed = output_format.model_validate_json(cleaned)
                return ChatInvokeCompletion(
                    completion=parsed,
                    usage=self._extract_usage(resp),
                    stop_reason=resp.choices[0].finish_reason if resp.choices else None,
                )
            raise ValueError("Model returned neither tool_calls nor JSON content.")

        # strategy == "prompt_json"
        import copy

        msgs_copy = copy.deepcopy(serialized_messages)
        schema_instruction = (
            "\n\nCRITICAL: Respond ONLY with a single valid JSON object matching this exact JSON Schema "
            "(no markdown prose outside JSON):\n"
            f"{json.dumps(optimized_schema, ensure_ascii=False)}"
        )
        if msgs_copy and msgs_copy[0].get("role") == "system" and isinstance(msgs_copy[0].get("content"), str):
            msgs_copy[0]["content"] += schema_instruction
        else:
            msgs_copy.append({"role": "user", "content": schema_instruction})

        resp = await self._call_with_transient_retry(
            lambda: client.chat.completions.create(
                model=model_id,
                messages=msgs_copy,
                **params,
            )
        )
        raw_content = (resp.choices[0].message.content or "") if resp.choices else ""
        cleaned = strip_reasoning_and_extract_json(raw_content)
        parsed = output_format.model_validate_json(cleaned)
        return ChatInvokeCompletion(
            completion=parsed,
            usage=self._extract_usage(resp),
            stop_reason=resp.choices[0].finish_reason if resp.choices else None,
        )


async def fetch_routeway_free_models(
    api_key: str = "",
    base_url: str = ROUTEWAY_BASE_URL,
) -> dict[str, Any]:
    """Fetch live catalog from https://api.routeway.ai/v1/models and filter strictly to $0.00 FREE chat models."""
    clean_base = (base_url or ROUTEWAY_BASE_URL).rstrip("/")
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(f"{clean_base}/models", headers=headers)
            r.raise_for_status()
            payload = r.json()

        free_models: list[dict[str, Any]] = []
        for item in payload.get("data", []):
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue
            if item.get("available") is False:
                continue
            endpoints = item.get("endpoints") or []
            if endpoints and "/v1/chat/completions" not in endpoints:
                continue

            pricing = item.get("pricing") or {}
            in_price = (pricing.get("input") or {}).get("price_per_million_t")
            out_price = (pricing.get("output") or {}).get("price_per_million_t")
            is_zero_cost = (in_price == 0 or in_price == 0.0) and (out_price == 0 or out_price == 0.0)
            is_free = model_id.endswith(":free") or is_zero_cost
            if not is_free:
                continue

            caps = item.get("capabilities") or {}
            vision = bool(caps.get("vision", False))
            fn_call = bool(caps.get("function_call", False))
            reasoning = bool(caps.get("reasoning", False))
            ctx_k = int((item.get("context_length") or 0) / 1000)
            display_name = item.get("short_name") or item.get("name") or model_id

            tags = ["رایگان $0"]
            tags.append("📸 دارای Vision" if vision else "📄 متنی")
            if fn_call:
                tags.append("⚡ ابزار/ایجنت")
            if ctx_k > 0:
                tags.append(f"{ctx_k}K")

            free_models.append(
                {
                    "id": model_id,
                    "label": f"{display_name} ({' • '.join(tags)})",
                    "vision": vision,
                    "function_call": fn_call,
                    "reasoning": reasoning,
                    "owned_by": item.get("owned_by", ""),
                }
            )

        # Sort: Vision + Function Call models first (best for Browser Use!), then Function Call, then rest
        free_models.sort(
            key=lambda m: (
                0 if (m["vision"] and m["function_call"]) else (1 if m["function_call"] else 2),
                m["id"],
            )
        )

        return {
            "ok": True,
            "models": free_models,
            "message_fa": f"✅ ارتباط با Routeway برقرار شد! تعداد {len(free_models)} مدل ۱۰۰٪ رایگان فعال پیدا شد.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "models": [],
            "message_fa": f"⚠️ خطا در دریافت لیست زنده از Routeway: {exc} (لیست پیش‌فرض مدل‌های رایگان همچنان در دسترس است).",
            "raw_error": str(exc),
        }
