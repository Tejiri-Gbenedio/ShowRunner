from app.agent_contracts import PackagingInput, PackagingOutput

class MockPackagingAgent:
    def run(self, input: PackagingInput) -> PackagingOutput:
        title = input.qa.production_id.replace("production-", "").replace("-", " ").title() + " — The Short"
        return PackagingOutput(input.preset.id, input.qa.production_id, f"{input.preset.id}-short.mp4", title, input.qa.scene_count, "A tightly edited short built from the selected channel preset.", (input.preset.niche, "shorts", "storytelling"))
