"""Small, provider-neutral OpenAI-compatible LLM client.

The default transport is deliberately stdlib-only.  A callable transport can be
injected by tests (or an embedding application), so provider code never needs a
live network connection in mock mode.
"""
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
    max_tokens: int = 800
    daily_cap: int = 50

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "mock").lower(),
            base_url=os.getenv("LLM_BASE_URL", ""), api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""), timeout=float(os.getenv("LLM_TIMEOUT", "30")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "800")),
            daily_cap=int(os.getenv("LLM_DAILY_CAP", "50")),
        )


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _http_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode())


class OpenAICompatibleProvider:
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
                   "temperature": 0.2, "max_tokens": self.config.max_tokens}
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        last: Exception | None = None
        for _ in range(2):
            self._calls += 1
            try:
                response = self.transport(self.config.base_url.rstrip("/") + "/chat/completions", headers, payload, self.config.timeout)
                content = response["choices"][0]["message"]["content"]
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
                value = json.loads(content)
                if not isinstance(value, dict):
                    raise ValueError("structured response must be an object")
                return validate(value)
            except Exception as exc:
                last = exc
        raise LLMError("LLM response failed validation after retry") from last


class MockLLMProvider:
    """Explicit no-network provider used by default application wiring."""
    def complete_json(self, prompt: str, validate: Callable[[dict[str, Any]], Any]) -> Any:
        raise LLMError("mock provider has no real completion")


def provider_from_env(transport: Transport | None = None) -> MockLLMProvider | OpenAICompatibleProvider:
    config = LLMConfig.from_env()
    return MockLLMProvider() if config.provider == "mock" else OpenAICompatibleProvider(config, transport, enforce_global_cap=True)
