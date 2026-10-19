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
            candidates = data.get("candidates", data)
            if isinstance(candidates, dict): candidates = [candidates]
            if not isinstance(candidates, list):
                raise ValueError("topic.candidates: expected object or list")
            for candidate in candidates:
                if not isinstance(candidate, dict): continue
                title = str(candidate.get("title", candidate.get("topic", ""))).strip()
                hook = str(candidate.get("hook", candidate.get("opening", ""))).strip()
                if not title or not hook: continue
                try: score = int(float(candidate.get("score", 0)))
                except (TypeError, ValueError): score = 0
                raw_reasons = candidate.get("reasons", candidate.get("reason", ()))
                if isinstance(raw_reasons, str): reasons = (raw_reasons.strip(),) if raw_reasons.strip() else ()
                elif isinstance(raw_reasons, list): reasons = tuple(str(x).strip() for x in raw_reasons if str(x).strip())
                else: reasons = ()
                return TopicOutput(title, input.preset.id, hook, score, reasons)
            raise ValueError("topic.title/hook: no usable candidate")
        return self.provider.complete_json(prompt, validate)
