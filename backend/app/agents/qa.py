from app.agent_contracts import QAInput, QAOutput

class MockQAAgent:
    def run(self, input: QAInput) -> QAOutput:
        checks = ("scene count is non-zero", "every scene has an asset key", "every scene has narration")
        issues = []
        if not input.production.scenes: issues.append("production has no scenes")
        if any(not scene.asset_key for scene in input.production.scenes): issues.append("scene asset key is missing")
        if any(not scene.narration.strip() for scene in input.production.scenes): issues.append("scene narration is missing")
        return QAOutput(input.preset.id, input.production.production_id, not issues, checks, tuple(issues), input.production.scene_count)
