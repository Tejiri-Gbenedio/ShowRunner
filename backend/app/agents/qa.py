from app.agent_contracts import QAInput, QAOutput, QACheck

class MockQAAgent:
    def run(self, input: QAInput) -> QAOutput:
        checks = tuple(input.preset.quality_rules)
        issues = []
        if not input.production.scenes: issues.append("production has no scenes")
        if any(not scene.asset_key for scene in input.production.scenes): issues.append("scene asset key is missing")
        if any(not scene.narration.strip() for scene in input.production.scenes): issues.append("scene narration is missing")
        if "Under 60 seconds" in checks and input.production.scene_count * input.preset.scene_length_seconds >= 60: issues.append("runtime is 60 seconds or longer")
        results = tuple(QACheck(label, not issues) for label in checks)
        return QAOutput(input.preset.id, input.production.production_id, not issues, checks, tuple(issues), input.production.scene_count, 100 if not issues else 40, results)
