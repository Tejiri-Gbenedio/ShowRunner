from app.agent_contracts import PackagingInput, PackagingOutput

class MockPackagingAgent:
    def run(self, input: PackagingInput) -> PackagingOutput:
        topic_title = input.topic.title if input.topic else input.preset.name
        script_title = input.script.title if input.script else topic_title
        title = f"{topic_title} | {input.preset.name}"
        slug = "-".join("".join(c.lower() if c.isalnum() else "-" for c in topic_title).split("-"))
        tags = tuple(dict.fromkeys(self._tag(x) for x in (input.preset.niche, topic_title, script_title, "shorts")))
        return PackagingOutput(input.preset.id, input.qa.production_id, f"{slug or input.preset.id}.mp4", title, input.qa.scene_count, f"{topic_title}: {input.preset.packaging_style} about {input.preset.niche}.", tags)

    @staticmethod
    def _tag(value: str) -> str:
        return "".join(c.lower() for c in value if c.isalnum())
