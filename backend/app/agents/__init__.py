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

_real_runs_by_day: dict[date, int] = {}

class AgentExecutionError(RuntimeError):
    def __init__(self, agent: str, cause: Exception) -> None:
        super().__init__(str(cause))
        self.agent = agent

def _run(agent: str, operation):
    try:
        return operation()
    except Exception as exc:
        raise AgentExecutionError(agent, exc) from exc

def run_offline_sequence(preset: ChannelPreset) -> OfflineRun:
    topic = _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
    script = _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
    production = _run("production", lambda: MockProductionAgent().run(ProductionInput(preset, script)))
    qa = _run("qa", lambda: MockQAAgent().run(QAInput(preset, production)))
    package = _run("packaging", lambda: MockPackagingAgent().run(PackagingInput(preset, qa)))
    return OfflineRun(topic, script, production, qa, package)

def run_pipeline(preset: ChannelPreset, provider=None) -> tuple[OfflineRun, str, str | None]:
    provider = provider or provider_from_env()
    real = provider.__class__.__name__ == "OpenAICompatibleProvider"
    mock_reason = None
    if real:
        if getattr(provider, "enforce_global_cap", False):
            today = date.today()
            cap = provider.config.daily_cap
            if cap >= 0 and _real_runs_by_day.get(today, 0) >= cap:
                mock_reason = "daily LLM run cap reached; used deterministic mock output"
                topic = _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
                script = _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
                production = _run("production", lambda: MockProductionAgent().run(ProductionInput(preset, script)))
                qa = _run("qa", lambda: MockQAAgent().run(QAInput(preset, production)))
                package = _run("packaging", lambda: MockPackagingAgent().run(PackagingInput(preset, qa)))
                return OfflineRun(topic, script, production, qa, package), "mock", mock_reason
            _real_runs_by_day[today] = _real_runs_by_day.get(today, 0) + 1
        try:
            topic = _run("topic", lambda: RealTopicAgent(provider).run(TopicInput(preset)))
            script = _run("script_scene", lambda: RealScriptSceneAgent(provider).run(ScriptSceneInput(preset, topic)))
        except AgentExecutionError as exc:
            if isinstance(exc.__cause__, LLMError) and "daily LLM request cap" in str(exc.__cause__):
                mock_reason = "daily LLM request cap reached; used deterministic mock output"
                topic = _run("topic", lambda: MockTopicAgent().run(TopicInput(preset)))
                script = _run("script_scene", lambda: MockScriptSceneAgent().run(ScriptSceneInput(preset, topic)))
            else:
                raise
    else:
        # Keep the established offline entry point as the mock integration seam.
        return run_offline_sequence(preset), "mock", None
    production = _run("production", lambda: MockProductionAgent().run(ProductionInput(preset, script)))
    qa = _run("qa", lambda: MockQAAgent().run(QAInput(preset, production)))
    package = _run("packaging", lambda: MockPackagingAgent().run(PackagingInput(preset, qa)))
    return OfflineRun(topic, script, production, qa, package), ("mock" if mock_reason else ("real" if real else "mock")), mock_reason

__all__ = ["AgentExecutionError", "MockPackagingAgent", "MockProductionAgent", "MockQAAgent", "MockScriptSceneAgent", "MockTopicAgent", "RealTopicAgent", "RealScriptSceneAgent", "run_offline_sequence", "run_pipeline"]
