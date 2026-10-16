from dataclasses import replace

from app.agents import (
    MockPackagingAgent,
    MockProductionAgent,
    MockQAAgent,
    MockScriptSceneAgent,
    MockTopicAgent,
    run_offline_sequence,
)
from app.agent_contracts import (
    PackagingInput,
    ProductionInput,
    QAInput,
    ScriptSceneInput,
    TopicInput,
    TopicOutput,
)
from app.presets import PRESETS


def test_contracts_are_typed_and_topic_output_is_immutable() -> None:
    output = TopicOutput("A lantern in the snow", "survival-thriller", "open with a radio signal")
    assert output.preset_id == "survival-thriller"
    try:
        output.title = "changed"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("contract output must be immutable")


def test_each_preset_has_handcrafted_topic_and_script_content() -> None:
    for preset in PRESETS:
        topic = MockTopicAgent().run(TopicInput(preset))
        script = MockScriptSceneAgent().run(ScriptSceneInput(preset, topic))
        assert topic.title and topic.title != "Lorem ipsum"
        assert script.scenes
        assert all(scene.narration.strip() for scene in script.scenes)
        assert script.scenes[0].duration_seconds == preset.scene_length_seconds


def test_adapter_substitution_changes_topic_generation() -> None:
    class EditorialAdapter:
        def complete_topic(self, prompt: str) -> str:
            assert "stoic-philosophy" in prompt
            return "The discipline of pausing before reacting"

    preset = PRESETS[1]
    topic = MockTopicAgent(adapter=EditorialAdapter()).run(TopicInput(preset))
    assert topic.title == "The discipline of pausing before reacting"


def test_offline_full_agent_sequence_is_deterministic_for_both_presets() -> None:
    for preset in PRESETS:
        first = run_offline_sequence(preset)
        second = run_offline_sequence(preset)
        assert first == second
        assert first.qa.passed is True
        assert first.package.filename.endswith(".mp4")
        assert first.package.scene_count == len(first.script.scenes)


def test_individual_agents_communicate_only_via_contract_inputs() -> None:
    preset = PRESETS[0]
    topic = MockTopicAgent().run(TopicInput(preset))
    script = MockScriptSceneAgent().run(ScriptSceneInput(preset, topic))
    production = MockProductionAgent().run(ProductionInput(preset, script))
    qa = MockQAAgent().run(QAInput(preset, production))
    package = MockPackagingAgent().run(PackagingInput(preset, qa))
    assert production.scene_count == len(script.scenes)
    assert qa.production_id == production.production_id
    assert package.qa_id == qa.production_id
