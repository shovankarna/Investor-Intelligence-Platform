"""Resilient OpenRouter API client with automatic retry backoff and model fallback."""

import asyncio
import json
import re
from typing import Any, TypeVar

import httpx
from langfuse import observe
from pydantic import BaseModel

from app.core.config import settings
from app.llm.schemas import LLMGenerationResult

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient:
    """Async HTTP client for OpenRouter with fallback chains and backoff."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.primary_model = settings.OPENROUTER_DEFAULT_MODEL
        self.fallback_chain = [self.primary_model] + [
            m for m in settings.OPENROUTER_FALLBACK_MODELS if m != self.primary_model
        ]

    def _get_headers(self) -> dict[str, str]:
        """Generate OpenRouter authentication and attribution headers."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": settings.APP_NAME,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @observe(as_type="generation")
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1500,
        response_format: dict[str, str] | None = None,
        max_retries_per_model: int = 2,
    ) -> LLMGenerationResult:
        """Send chat completion request with multi-model fallback on 429/5xx errors."""
        last_exception: Exception | None = None

        async with httpx.AsyncClient(timeout=45.0) as client:
            # Try each model in the fallback chain in order
            for model_id in self.fallback_chain:
                for attempt in range(max_retries_per_model):
                    try:
                        payload: dict[str, Any] = {
                            "model": model_id,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        if response_format:
                            payload["response_format"] = response_format

                        print(f"      📡 [LLM Call] Invoking model '{model_id}' (temp={temperature}, max_tokens={max_tokens})...", flush=True)

                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=self._get_headers(),
                            json=payload,
                        )

                        # Handle rate limits (429) or server errors (5xx) with backoff
                        if response.status_code == 429 or response.status_code >= 500:
                            wait_seconds = (2**attempt) + 0.5
                            print(
                                f"      ⚠️ [OpenRouter] HTTP {response.status_code} on {model_id}. Retrying in {wait_seconds:.1f}s...", flush=True
                            )
                            await asyncio.sleep(wait_seconds)
                            continue

                        response.raise_for_status()
                        data = response.json()

                        # Extract text and token usage
                        choices = data.get("choices", [])
                        if not choices:
                            raise ValueError(f"No completion choices returned by model {model_id}")

                        raw_content = choices[0].get("message", {}).get("content") or ""
                        usage = data.get("usage", {})
                        p_tok = usage.get("prompt_tokens", 0)
                        c_tok = usage.get("completion_tokens", 0)
                        t_tok = usage.get("total_tokens", 0)

                        print(f"      ✨ [LLM Response] Success from '{model_id}' | Tokens: {p_tok} prompt + {c_tok} completion = {t_tok} total", flush=True)
                        preview = raw_content[:150].replace('\n', ' ')
                        print(f"      📝 [LLM Output Preview]: {preview}...", flush=True)

                        return LLMGenerationResult(
                            raw_text=raw_content,
                            model_used=model_id,
                            prompt_tokens=p_tok,
                            completion_tokens=c_tok,
                            total_tokens=t_tok,
                        )

                    except (
                        httpx.HTTPStatusError,
                        httpx.RequestError,
                        ValueError,
                    ) as exc:
                        last_exception = exc
                        wait_seconds = (2**attempt) + 0.5
                        print(
                            f"[WARN] [OpenRouter] Error on model '{model_id}' (attempt {attempt + 1}): {exc}"
                        )
                        await asyncio.sleep(wait_seconds)

                print(
                    f"[ERROR] [OpenRouter] Exhausted retries for '{model_id}'. Failing over to next fallback model..."
                )

        raise RuntimeError(f"All models in fallback chain failed. Last error: {last_exception}")

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> T:
        """Forces JSON output and parses the response directly into a Pydantic model."""
        # Inject JSON schema expectation into the request
        result = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        raw_text = result.raw_text.strip()

        # 1. Try matching markdown code blocks: ```json ... ``` or ``` ... ```
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            try:
                parsed_dict = json.loads(candidate)
                return schema.model_validate(parsed_dict)
            except Exception:
                pass

        # 2. Try parsing raw text directly
        try:
            parsed_dict = json.loads(raw_text)
            return schema.model_validate(parsed_dict)
        except Exception:
            pass

        # 3. Find outermost JSON object { ... }
        first_brace = raw_text.find("{")
        last_brace = raw_text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = raw_text[first_brace : last_brace + 1]
            try:
                parsed_dict = json.loads(candidate)
                return schema.model_validate(parsed_dict)
            except Exception:
                pass

        # 4. Find outermost JSON array [ ... ] if schema allows root list
        first_bracket = raw_text.find("[")
        last_bracket = raw_text.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            candidate = raw_text[first_bracket : last_bracket + 1]
            try:
                parsed_dict = json.loads(candidate)
                return schema.model_validate(parsed_dict)
            except Exception:
                pass

        raise ValueError(
            f"Failed to parse structured JSON into schema {schema.__name__}. "
            f"Raw output: {result.raw_text}"
        )


# Module-level singleton instance
llm_client = OpenRouterClient()
