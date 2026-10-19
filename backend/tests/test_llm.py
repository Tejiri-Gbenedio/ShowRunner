import pytest

from app.llm import LLMConfig, LLMError, OpenAICompatibleProvider, provider_from_env
from app.agents import run_pipeline
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


@pytest.mark.parametrize("body", ["not json", '{"ok": 1}'])
def test_malformed_or_schema_invalid_retries_then_fails(body):
    p, calls = provider([body, body])
    with pytest.raises(LLMError):
        p.complete_json("x", lambda d: d["missing"])
    assert len(calls) == 2


def test_timeout_retries_then_fails():
    p, calls = provider([TimeoutError(), TimeoutError()])
    with pytest.raises(LLMError):
        p.complete_json("x", lambda d: d)
    assert len(calls) == 2


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
