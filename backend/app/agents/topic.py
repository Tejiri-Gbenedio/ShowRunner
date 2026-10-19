from app.agent_contracts import TopicAdapter, TopicInput, TopicOutput
from app.llm import OpenAICompatibleProvider

TOPICS = {
    "survival-thriller": ("The Radio That Answered Back", "A dead radio crackles from beneath the snow."),
    "stoic-philosophy": ("The Pause Before the Answer", "Your next response begins in the breath you take first."),
}

class DeterministicTopicAdapter:
    def complete_topic(self, prompt: str) -> str:
        preset_id = prompt.rsplit("preset=", 1)[-1]
        return TOPICS[preset_id][0]

class MockTopicAgent:
    def __init__(self, adapter: TopicAdapter | None = None) -> None:
        self.adapter = adapter or DeterministicTopicAdapter()

    def run(self, input: TopicInput) -> TopicOutput:
        title = self.adapter.complete_topic(f"Create a short topic for preset={input.preset.id}")
        hook = TOPICS.get(input.preset.id, (title, "A precise idea deserves a clear opening."))[1]
        reasons = ("Immediate hook for the opening seconds", "Clear visual premise", "Strong curiosity gap")
        return TopicOutput(title, input.preset.id, hook, 90, reasons)


class RealTopicAgent:
    def __init__(self, provider: OpenAICompatibleProvider) -> None:
        self.provider = provider

    def run(self, input: TopicInput) -> TopicOutput:
        prompt = f"Return JSON with title, hook, score, reasons for a {input.preset.niche} channel. Tone: {input.preset.tone}. Audience: short-form viewers. Preset: {input.preset.id}."
        def validate(data: dict) -> TopicOutput:
            title, hook = data["title"], data["hook"]
            score, reasons = data["score"], data["reasons"]
            if not isinstance(title, str) or not isinstance(hook, str) or not isinstance(score, int) or not isinstance(reasons, list) or not all(isinstance(x, str) for x in reasons):
                raise ValueError("invalid topic schema")
            return TopicOutput(title, input.preset.id, hook, score, tuple(reasons))
        return self.provider.complete_json(prompt, validate)
