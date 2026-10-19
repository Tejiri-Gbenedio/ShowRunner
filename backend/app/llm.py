"""Small, provider-neutral OpenAI-compatible LLM client."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "mock"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout: float = 30.0
    max_tokens: int = 2000
    daily_cap: int = 50
    reasoning_effort: str = "low"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        effort = os.getenv("LLM_REASONING_EFFORT", "low").lower()
        if effort not in {"low", "medium", "high"}:
            effort = "low"
        return cls(
            provider=os.getenv("LLM_PROVIDER", "mock").lower(),
            base_url=os.getenv("LLM_BASE_URL", ""), api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""), timeout=float(os.getenv("LLM_TIMEOUT", "30")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            daily_cap=int(os.getenv("LLM_DAILY_CAP", "50")), reasoning_effort=effort,
        )


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _http_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode())


def _strip_markdown_fence(content: str) -> str:
    content = content.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.I | re.S)
    return match.group(1).strip() if match else content


class OpenAICompatibleProvider:
    JSON_RESERVE_TOKENS = 128

    def __init__(self, config: LLMConfig | None = None, transport: Transport | None = None, enforce_global_cap: bool = False) -> None:
        self.config = config or LLMConfig.from_env()
        self.transport = transport or _http_transport
        self._calls = 0
        self.enforce_global_cap = enforce_global_cap

    def complete_json(self, prompt: str, validate: Callable[[dict[str, Any]], Any]) -> Any:
        if self.config.daily_cap >= 0 and self._calls >= self.config.daily_cap:
            raise LLMError("daily LLM request cap reached")
        if not self.config.base_url or not self.config.model:
            raise LLMError("LLM_BASE_URL and LLM_MODEL are required for a real provider")
        payload = {"model": self.config.model, "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.2, "max_tokens": max(1, self.config.max_tokens - self.JSON_RESERVE_TOKENS),
                   "response_format": {"type": "json_object"}, "reasoning_effort": self.config.reasoning_effort}
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        last: Exception | None = None
        retry_prompt = prompt
        for attempt in range(3):
            self._calls += 1
            raw_preview = ""
            try:
                request_payload = dict(payload)
                request_payload["messages"] = [{"role": "user", "content": retry_prompt}]
                response = self.transport(self.config.base_url.rstrip("/") + "/chat/completions", headers, request_payload, self.config.timeout)
                choice = response.get("choices", [{}])[0]
                finish_reason = choice.get("finish_reason")
                if finish_reason and finish_reason not in {"stop", "end_turn"}:
                    raise ValueError(f"response.finish_reason: {finish_reason}")
                content = (choice.get("message") or {}).get("content")
                if isinstance(content, str):
                    raw_preview = re.sub(r"[\x00-\x1f\r\n]+", " ", content)[:300]
                    raw_preview = re.sub(r"(?:sk|key|token)[-_][A-Za-z0-9_-]{8,}", "[REDACTED]", raw_preview, flags=re.I)
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("response.content: empty")
                try:
                    value = json.loads(_strip_markdown_fence(content))
                except json.JSONDecodeError as parse_error:
                    raise ValueError(f"response.json: {parse_error.msg}; raw={raw_preview!r}") from parse_error
                if not isinstance(value, dict):
                    raise ValueError("response.json: structured response must be an object")
                return validate(value)
            except Exception as exc:
                last = exc
                detail = re.sub(r"[\x00-\x1f\r\n]+", " ", str(exc)).strip()[:300]
                if raw_preview and "raw=" not in detail:
                    detail = f"{detail}; raw={raw_preview!r}"[:300]
                if attempt < 2:
                    retry_prompt = f"Return only corrected JSON. Previous attempt error: {detail}"
        detail = re.sub(r"[\x00-\x1f\r\n]+", " ", str(last or "unknown error")).strip()[:300]
        raise LLMError(f"LLM response failed after 3 attempts: {detail}") from last


class MockLLMProvider:
    def complete_json(self, prompt: str, validate: Callable[[dict[str, Any]], Any]) -> Any:
        raise LLMError("mock provider has no real completion")


def provider_from_env(transport: Transport | None = None) -> MockLLMProvider | OpenAICompatibleProvider:
    config = LLMConfig.from_env()
    return MockLLMProvider() if config.provider == "mock" else OpenAICompatibleProvider(config, transport, enforce_global_cap=True)
