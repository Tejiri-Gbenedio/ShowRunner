from app.agent_contracts import OfflineRun, PackagingInput, ProductionInput, QAInput, ScriptSceneInput, TopicInput
from app.agents.packaging import MockPackagingAgent
from app.agents.production import MockProductionAgent
from app.agents.qa import MockQAAgent
from app.agents.script_scene import MockScriptSceneAgent
from app.agents.topic import MockTopicAgent
from app.presets import ChannelPreset


def run_offline_sequence(preset: ChannelPreset) -> OfflineRun:
    topic = MockTopicAgent().run(TopicInput(preset))
    script = MockScriptSceneAgent().run(ScriptSceneInput(preset, topic))
    production = MockProductionAgent().run(ProductionInput(preset, script))
    qa = MockQAAgent().run(QAInput(preset, production))
    package = MockPackagingAgent().run(PackagingInput(preset, qa))
    return OfflineRun(topic, script, production, qa, package)

__all__ = ["MockPackagingAgent", "MockProductionAgent", "MockQAAgent", "MockScriptSceneAgent", "MockTopicAgent", "run_offline_sequence"]
