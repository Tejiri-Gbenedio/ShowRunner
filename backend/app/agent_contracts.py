"""Typed boundaries shared by the five Step 2 agents."""
from dataclasses import dataclass
from typing import Protocol

from app.presets import ChannelPreset


class TopicAdapter(Protocol):
    def complete_topic(self, prompt: str) -> str: ...


class ScriptAdapter(Protocol):
    def complete_script(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class TopicInput:
    preset: ChannelPreset

@dataclass(frozen=True)
class TopicOutput:
    title: str
    preset_id: str
    hook: str
    score: int = 0
    reasons: tuple[str, ...] = ()

@dataclass(frozen=True)
class ScriptSceneInput:
    preset: ChannelPreset
    topic: TopicOutput

@dataclass(frozen=True)
class Scene:
    scene_number: int
    duration_seconds: int
    visual_direction: str
    narration: str

@dataclass(frozen=True)
class ScriptSceneOutput:
    preset_id: str
    title: str
    scenes: tuple[Scene, ...]

@dataclass(frozen=True)
class ProductionInput:
    preset: ChannelPreset
    script: ScriptSceneOutput

@dataclass(frozen=True)
class ProducedScene:
    scene_number: int
    asset_key: str
    narration: str

@dataclass(frozen=True)
class ProductionOutput:
    preset_id: str
    production_id: str
    scenes: tuple[ProducedScene, ...]
    scene_count: int

@dataclass(frozen=True)
class QAInput:
    preset: ChannelPreset
    production: ProductionOutput

@dataclass(frozen=True)
class QAOutput:
    preset_id: str
    production_id: str
    passed: bool
    checks: tuple[str, ...]
    issues: tuple[str, ...]
    scene_count: int
    score: int = 0
    check_results: tuple["QACheck", ...] = ()

@dataclass(frozen=True)
class QACheck:
    label: str
    passed: bool

@dataclass(frozen=True)
class PackagingInput:
    preset: ChannelPreset
    qa: QAOutput

@dataclass(frozen=True)
class PackagingOutput:
    preset_id: str
    qa_id: str
    filename: str
    title: str
    scene_count: int
    description: str = ""
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class OfflineRun:
    topic: TopicOutput
    script: ScriptSceneOutput
    production: ProductionOutput
    qa: QAOutput
    package: PackagingOutput
