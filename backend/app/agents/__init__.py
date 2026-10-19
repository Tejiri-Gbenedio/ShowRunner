from app.agent_contracts import OfflineRun, PackagingInput, ProductionInput, QAInput, ScriptSceneInput, TopicInput
from app.agents.packaging import MockPackagingAgent
from app.agents.production import MockProductionAgent
from app.agents.qa import MockQAAgent
from app.agents.script_scene import MockScriptSceneAgent
from app.agents.topic import MockTopicAgent
from app.presets import ChannelPreset

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

__all__ = ["AgentExecutionError", "MockPackagingAgent", "MockProductionAgent", "MockQAAgent", "MockScriptSceneAgent", "MockTopicAgent", "run_offline_sequence"]
