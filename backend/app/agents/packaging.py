from app.agent_contracts import PackagingInput, PackagingOutput

class MockPackagingAgent:
    def run(self, input: PackagingInput) -> PackagingOutput:
        return PackagingOutput(input.preset.id, input.qa.production_id, f"{input.preset.id}-short.mp4", input.qa.production_id, input.qa.scene_count)
