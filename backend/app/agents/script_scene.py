from app.agent_contracts import Scene, ScriptSceneInput, ScriptSceneOutput
from app.llm import OpenAICompatibleProvider

class MockScriptSceneAgent:
    def run(self, input: ScriptSceneInput) -> ScriptSceneOutput:
        p = input.preset
        if p.id == "survival-thriller":
            lines = (("Snow buries the trail as the radio clicks alive.", "A gloved hand brushes ice from a battered radio."), ("The reply uses a call sign nobody has heard in twenty years.", "A red frequency display pulses in the dark."), ("One flare remains; the signal answers from beyond the ridge.", "A lone amber flare stains the blue storm."))
        else:
            lines = (("Before answering, notice the space between the event and your judgment.", "A hand rests above a blank page at dawn."), ("That pause is not passivity; it is where choice becomes possible.", "Ink marks one deliberate line on the page."), ("Practice it once today: name what is yours to control, then act there.", "The page folds beside a warm cup of tea."))
        scenes = tuple(Scene(i, p.scene_length_seconds, visual, narration) for i, (narration, visual) in enumerate(lines, 1))
        return ScriptSceneOutput(p.id, input.topic.title, scenes)


class RealScriptSceneAgent:
    def __init__(self, provider: OpenAICompatibleProvider) -> None:
        self.provider = provider

    def run(self, input: ScriptSceneInput) -> ScriptSceneOutput:
        def validate(data: dict) -> ScriptSceneOutput:
            if "scenes" not in data:
                raise ValueError("script_scene field scenes: missing")
            raw = data["scenes"]
            if isinstance(raw, dict): raw = list(raw.values())
            if not isinstance(raw, list) or not raw:
                raise ValueError("script_scene.scenes: invalid script schema")
            scenes = []
            for index, item in enumerate(raw, 1):
                if not isinstance(item, dict): raise ValueError(f"script_scene.scenes[{index - 1}]: expected object")
                narration = item.get("narration", item.get("voiceover", item.get("voice_over", item.get("narrator"))))
                visual = item.get("visual_direction", item.get("visual", item.get("visuals")))
                if not isinstance(narration, str) or not narration.strip(): raise ValueError(f"script_scene.scenes[{index - 1}].narration: unusable")
                if not isinstance(visual, str) or not visual.strip(): raise ValueError(f"script_scene.scenes[{index - 1}].visual_direction: unusable")
                try: duration = int(float(item.get("duration_seconds", item.get("duration", input.preset.scene_length_seconds))))
                except (TypeError, ValueError): raise ValueError(f"script_scene.scenes[{index - 1}].duration_seconds: invalid")
                try: number = int(item.get("scene_number", item.get("scene", index)))
                except (TypeError, ValueError): number = index
                scenes.append(Scene(number, duration, visual.strip(), narration.strip()))
            scenes = tuple(scenes)
            if any(scene.duration_seconds != input.preset.scene_length_seconds for scene in scenes):
                raise ValueError("script_scene.scenes.duration_seconds: does not match preset")
            return ScriptSceneOutput(input.preset.id, input.topic.title, scenes)
        return self.provider.complete_json(f"Return JSON scenes for topic {input.topic.title}. Use exactly {input.preset.scene_length_seconds} seconds per scene and follow quality rules: {input.preset.quality_rules}.", validate)
