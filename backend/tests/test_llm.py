import pytest

from app.llm import LLMConfig, LLMError, OpenAICompatibleProvider, provider_from_env
from app.agents import AgentExecutionError, run_pipeline
from app.presets import PRESETS


def provider(responses, **kwargs):
    calls = []
    def transport(url, headers, payload, timeout):
        calls.append(url)
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return {"choices": [{"message": {"content": value}}]}
    return OpenAICompatibleProvider(LLMConfig(base_url="https://example.test/v1", model="m", daily_cap=10, **kwargs), transport), calls


def test_valid_structured_response():
    p, _ = provider(['{"ok": true}'])
    assert p.complete_json("x", lambda d: d["ok"]) is True


def test_markdown_json_fence_and_json_mode_are_supported():
    seen = []
    def transport(url, headers, payload, timeout):
        seen.append(payload)
        return {"choices": [{"message": {"content": "```json\n{\"ok\": true}\n```"}}]}
    p = OpenAICompatibleProvider(LLMConfig(base_url="https://example.test", model="m", max_tokens=200,
                                           reasoning_effort="medium"), transport)
    assert p.complete_json("private prompt", lambda d: d["ok"]) is True
    assert seen[0]["response_format"] == {"type": "json_object"}
    assert seen[0]["reasoning_effort"] == "medium"
    assert seen[0]["max_tokens"] == 72


def test_retry_prompt_contains_safe_validation_detail():
    prompts = []
    def transport(url, headers, payload, timeout):
        prompts.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": "{}"}}]}
    p = OpenAICompatibleProvider(LLMConfig(base_url="https://example.test", model="m"), transport)
    with pytest.raises(LLMError, match="missing required"):
        p.complete_json("secret API key is never echoed", lambda d: (_ for _ in ()).throw(ValueError("missing required field")))
    assert "missing required field" in prompts[1]


@pytest.mark.parametrize("body", ["not json", '{"ok": 1}'])
def test_malformed_or_schema_invalid_retries_then_fails(body):
    p, calls = provider([body, body])
    with pytest.raises(LLMError):
        p.complete_json("x", lambda d: d["missing"])
    assert len(calls) == 3


def test_timeout_retries_then_fails():
    p, calls = provider([TimeoutError(), TimeoutError()])
    with pytest.raises(LLMError):
        p.complete_json("x", lambda d: d)
    assert len(calls) == 3


def test_retry_succeeds():
    p, calls = provider(["bad", '{"ok": true}'])
    assert p.complete_json("x", lambda d: d["ok"]) is True
    assert len(calls) == 2


def test_mock_provider_never_requests():
    calls = []
    p = provider_from_env(lambda *args: calls.append(args))
    assert p.__class__.__name__ == "MockLLMProvider"
    assert calls == []

def test_pipeline_real_topic_and_script_with_injected_transport_stays_offline():
    responses = ['{"title":"Injected topic","hook":"Hook","score":88,"reasons":["reason"]}',
                 '{"scenes":[{"scene_number":1,"duration_seconds":6,"visual_direction":"Wide","narration":"Narrate"}]}']
    p, calls = provider(responses)
    result, mode, reason = run_pipeline(PRESETS[0], p)
    assert mode == "real" and reason is None
    assert result.topic.title == "Injected topic"
    assert result.script.scenes[0].narration == "Narrate"
    assert len(calls) == 2


def test_real_topic_failure_falls_back_only_topic_when_enabled(monkeypatch):
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "true")
    p, calls = provider([TimeoutError(), TimeoutError(), TimeoutError(),
                         '{"scenes":[{"scene_number":1,"duration_seconds":6,"visual_direction":"Wide","narration":"Narrate"}]}'])
    result, mode, reason = run_pipeline(PRESETS[0], p)
    assert mode == "mock"
    assert reason.startswith("real LLM failed; mock fallback used")
    assert "topic" in reason and "after 3 attempts" in reason
    assert result.topic.title
    assert result.script.scenes[0].narration == "Narrate"
    assert len(calls) == 4


def test_real_script_failure_falls_back_only_script_when_enabled(monkeypatch):
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "true")
    p, _ = provider(['{"title":"Injected topic","hook":"Hook","score":88,"reasons":["reason"]}',
                     TimeoutError(), TimeoutError(), TimeoutError()])
    result, mode, reason = run_pipeline(PRESETS[0], p)
    assert mode == "mock"
    assert reason.startswith("real LLM failed; mock fallback used")
    assert "script_scene" in reason
    assert result.topic.title == "Injected topic"
    assert result.script.scenes


def test_real_failure_is_short_diagnostic_when_fallback_disabled(monkeypatch):
    monkeypatch.delenv("LLM_FALLBACK_TO_MOCK", raising=False)
    p, _ = provider([TimeoutError(), TimeoutError(), TimeoutError()])
    with pytest.raises(AgentExecutionError, match="LLM response failed after 3 attempts") as failure:
        run_pipeline(PRESETS[0], p)
    assert failure.value.agent == "topic"
