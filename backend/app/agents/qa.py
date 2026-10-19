from app.agent_contracts import QAInput, QAOutput, QACheck

class MockQAAgent:
    def run(self, input: QAInput) -> QAOutput:
        scenes = input.production.scenes
        checks = ("total duration", "each scene duration", "narration word fit", "hook in scene 1", "banned words/topics")
        text = " ".join(s.narration for s in scenes).lower()
        reasons = {
            "total duration": "ok" if input.production.total_duration_seconds <= input.preset.target_duration_seconds else "total duration exceeds preset target",
            "each scene duration": "ok" if all((s.duration_seconds or input.preset.scene_length_seconds) == input.preset.scene_length_seconds for s in scenes) else "one or more scene durations differ from preset",
            "narration word fit": "ok" if all(len(s.narration.split()) <= (s.duration_seconds or input.preset.scene_length_seconds) * input.preset.speaking_rate_wpm / 60 for s in scenes) else "narration exceeds speaking-rate word budget",
            "hook in scene 1": "ok" if scenes and scenes[0].narration.strip() else "scene 1 has no hook",
            "banned words/topics": "ok" if not any(b.lower() in text for b in (*input.preset.banned_words, *input.preset.banned_topics)) else "narration contains a banned word or topic",
        }
        results = tuple(QACheck(label, reasons[label] == "ok", reasons[label]) for label in checks)
        issues = tuple(f"{r.label}: {r.reason}" for r in results if not r.passed)
        score = round(100 * sum(r.passed for r in results) / len(results))
        return QAOutput(input.preset.id, input.production.production_id, not issues, checks, issues, input.production.scene_count, score, results)
