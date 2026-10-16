from app.agent_contracts import ProductionInput, ProductionOutput, ProducedScene

class MockProductionAgent:
    def run(self, input: ProductionInput) -> ProductionOutput:
        scenes = tuple(ProducedScene(s.scene_number, f"{input.preset.id}/scene-{s.scene_number:02d}", s.narration) for s in input.script.scenes)
        return ProductionOutput(input.preset.id, f"production-{input.preset.id}", scenes, len(scenes))
