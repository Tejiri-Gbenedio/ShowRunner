from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class ChannelPreset:
    id: str
    name: str
    niche: str
    tone: str
    scene_length_seconds: int
    visual_style: str
    voice_settings: dict[str, str]
    quality_rules: tuple[str, ...]

PRESETS = (
    ChannelPreset("survival-thriller", "Last Signal", "survival-story thriller", "tense, cinematic, restrained", 6, "cold blue night footage with amber emergency light", {"voice": "low male narrator", "pace": "urgent but intelligible"}, ("Hook within 2 seconds", "No graphic claims", "Escalation every scene", "Under 60 seconds")),
    ChannelPreset("stoic-philosophy", "The Quiet Discipline", "stoic philosophy", "calm, reflective, practical", 8, "minimal stone, paper, dawn light, slow camera movement", {"voice": "warm neutral narrator", "pace": "measured"}, ("One practical lesson", "Accurate attribution", "Clear takeaway", "Under 60 seconds")),
)

def list_presets() -> list[dict]:
    return [asdict(p) for p in PRESETS]
