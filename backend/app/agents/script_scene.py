from app.agent_contracts import Scene, ScriptSceneInput, ScriptSceneOutput

class MockScriptSceneAgent:
    def run(self, input: ScriptSceneInput) -> ScriptSceneOutput:
        p = input.preset
        if p.id == "survival-thriller":
            lines = (("Snow buries the trail as the radio clicks alive.", "A gloved hand brushes ice from a battered radio."), ("The reply uses a call sign nobody has heard in twenty years.", "A red frequency display pulses in the dark."), ("One flare remains; the signal answers from beyond the ridge.", "A lone amber flare stains the blue storm."))
        else:
            lines = (("Before answering, notice the space between the event and your judgment.", "A hand rests above a blank page at dawn."), ("That pause is not passivity; it is where choice becomes possible.", "Ink marks one deliberate line on the page."), ("Practice it once today: name what is yours to control, then act there.", "The page folds beside a warm cup of tea."))
        scenes = tuple(Scene(i, p.scene_length_seconds, visual, narration) for i, (narration, visual) in enumerate(lines, 1))
        return ScriptSceneOutput(p.id, input.topic.title, scenes)
