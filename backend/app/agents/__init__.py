from app.agent_contracts import OfflineRun, PackagingInput, ProductionInput, QAInput, ScriptSceneInput, TopicInput
from app.agents.packaging import MockPackagingAgent
from app.agents.production import MockProductionAgent
from app.agents.qa import MockQAAgent
from app.agents.script_scene import MockScriptSceneAgent
from app.agents.topic import MockTopicAgent, RealTopicAgent
from app.agents.script_scene import RealScriptSceneAgent
from app.llm import LLMError, provider_from_env
from app.presets import ChannelPreset
from datetime import date
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

_real_runs_by_day: dict[date, int] = {}

class AgentExecutionError(RuntimeError):
    def __init__(self, agent: str, cause: Exception) -> None:
        super().__init__(str(cause))
        self.agent = agent

def _run(agent: str, operation):
    timeout = float(os.getenv("PIPELINE_AGENT_TIMEOUT_SECONDS", os.getenv("AGENT_TIMEOUT_SECONDS", "30")))
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(operation).result(timeout=timeout)
    except FutureTimeout as exc:
        raise AgentExecutionError(agent, TimeoutError(f"{agent} exceeded {timeout:g}s timeout")) from exc
    except Exception as exc:
        raise AgentExecutionError(agent, exc) from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

def run_offline_sequence(preset: ChannelPreset) -> OfflineRun:
    topic = _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
    script = _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
    production = _run("production", lambda: MockProductionAgent().run(ProductionInput(preset, script)))
    qa = _run("qa", lambda: MockQAAgent().run(QAInput(preset, production)))
    package = _run("packaging", lambda: MockPackagingAgent().run(PackagingInput(preset, qa, topic, script)))
    return OfflineRun(topic, script, production, qa, package)

def _fallback_enabled() -> bool:
    return os.getenv("LLM_FALLBACK_TO_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}


def _mock_topic_and_script(preset, topic=None, script=None):
    topic = topic or _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
    script = script or _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
    return topic, script


def _fallback_reason(exc: AgentExecutionError) -> str:
    cause = str(exc.__cause__ or exc).replace("\n", " ").strip()[:300]
    return f"real LLM failed; mock fallback used ({exc.agent}: {cause})"


def run_pipeline(preset: ChannelPreset, provider=None) -> tuple[OfflineRun, str, str | None]:
    provider = provider or provider_from_env()
    real = provider.__class__.__name__ == "OpenAICompatibleProvider"
    mock_reason = None
    if not real:
        return run_offline_sequence(preset), "mock", None
    if getattr(provider, "enforce_global_cap", False):
        today = date.today()
        cap = provider.config.daily_cap
        if cap >= 0 and _real_runs_by_day.get(today, 0) >= cap:
            mock_reason = "daily LLM request cap reached; used deterministic mock output"
            topic, script = _mock_topic_and_script(preset)
        else:
            _real_runs_by_day[today] = _real_runs_by_day.get(today, 0) + 1
            topic = script = None
    else:
        topic = script = None
    if topic is None:
        try:
            topic = _run("topic", lambda: RealTopicAgent(provider).run(TopicInput(preset)))
        except AgentExecutionError as exc:
            if not _fallback_enabled():
                raise
            mock_reason = _fallback_reason(exc)
            topic = _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
    if script is None:
        try:
            script = _run("script_scene", lambda: RealScriptSceneAgent(provider).run(ScriptSceneInput(preset, topic)))
        except AgentExecutionError as exc:
            if not _fallback_enabled():
                raise
            mock_reason = _fallback_reason(exc) if mock_reason is None else f"{mock_reason}; {_fallback_reason(exc)}"
            script = _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
    production = _run("production", lambda: MockProductionAgent().run(ProductionInput(preset, script)))
    qa = _run("qa", lambda: MockQAAgent().run(QAInput(preset, production)))
    package = _run("packaging", lambda: MockPackagingAgent().run(PackagingInput(preset, qa, topic, script)))
    return OfflineRun(topic, script, production, qa, package), ("mock" if mock_reason else "real"), mock_reason


__all__ = ["AgentExecutionError", "MockPackagingAgent", "MockProductionAgent", "MockQAAgent", "MockScriptSceneAgent", "MockTopicAgent", "RealTopicAgent", "RealScriptSceneAgent", "run_offline_sequence", "run_pipeline"]
