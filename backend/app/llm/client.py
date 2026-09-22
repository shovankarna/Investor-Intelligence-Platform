"""Resilient OpenRouter API client with automatic retry backoff and model fallback."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.llm.schemas import LLMGenerationResult

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient:
    """Async HTTP client for OpenRouter with fallback chains and backoff."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.primary_model = settings.OPENROUTER_DEFAULT_MODEL
        self.fallback_chain = [self.primary_model] + [
            m for m in settings.OPENROUTER_FALLBACK_MODELS if m != self.primary_model
        ]

    def _get_headers(self) -> Dict[str, str]:
        """Generate OpenRouter authentication and attribution headers."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": settings.APP_NAME,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1500,
        response_format: Optional[Dict[str, str]] = None,
        max_retries_per_model: int = 2,
    ) -> LLMGenerationResult:
        """Send chat completion request with multi-model fallback on 429/5xx errors."""
        last_exception: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=45.0) as client:
            # Try each model in the fallback chain in order
            for model_id in self.fallback_chain:
                for attempt in range(max_retries_per_model):
                    try:
                        payload: Dict[str, Any] = {
                            "model": model_id,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        if response_format:
                            payload["response_format"] = response_format

                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=self._get_headers(),
                            json=payload,
                        )

                        # Handle rate limits (429) or server errors (5xx) with backoff
                        if response.status_code == 429 or response.status_code >= 500:
                            wait_seconds = (2**attempt) + 0.5
                            print(
                                f"⚠️ [OpenRouter] HTTP {response.status_code} on {model_id}. Retrying in {wait_seconds:.1f}s..."
                            )
                            await asyncio.sleep(wait_seconds)
                            continue

                        response.raise_for_status()
                        data = response.json()

                        # Extract text and token usage
                        choices = data.get("choices", [])
                        if not choices:
                            raise ValueError(
                                f"No completion choices returned by model {model_id}"
                            )

                        raw_content = choices[0].get("message", {}).get("content", "")
                        usage = data.get("usage", {})

                        return LLMGenerationResult(
                            raw_text=raw_content,
                            model_used=model_id,
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                        )

                    except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                        last_exception = exc
                        wait_seconds = (2**attempt) + 0.5
                        print(
                            f"⚠️ [OpenRouter] Error on model '{model_id}' (attempt {attempt + 1}): {exc}"
                        )
                        await asyncio.sleep(wait_seconds)

                print(
                    f"❌ [OpenRouter] Exhausted retries for '{model_id}'. Failing over to next fallback model..."
                )

        raise RuntimeError(
            f"All models in fallback chain failed. Last error: {last_exception}"
        )

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type[T],
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

        try:
            cleaned_text = result.raw_text.strip()
            # Strip markdown code blocks if the model wrapped output in ```json ... ```
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            parsed_dict = json.loads(cleaned_text.strip())
            return schema.model_validate(parsed_dict)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse structured JSON into schema {schema.__name__}. "
                f"Raw output: {result.raw_text}"
            ) from exc


# Module-level singleton instance
llm_client = OpenRouterClient()
