"""Stage 1 — StructuredScript Pydantic models.

Mirrors the JSON Schema defined in docs/schema-design.md §Stage 1 Output Schema.
These models are used with LLM's with_structured_output() for type-safe generation.

Schema hierarchy:
  StructuredScript
    ├── GlobalContext (story_world, power_system, timeline, continuity_rules)
    ├── Episode[] ─── Scene[] ─── SceneContent ─── ScriptSegment[]
    │               ├── SceneLocation
    │               └── CharacterPresent[]
    ├── CharacterIndexEntry[]
    ├── LocationIndexEntry[]
    └── PropIndexEntry[]
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Enums ──


class SegmentType(str, Enum):
    NARRATION = "narration"
    DIALOGUE = "dialogue"
    ACTION = "action"
    INNER_MONOLOGUE = "inner_monologue"
    VOICE_OVER = "voice_over"
    TRANSITION = "transition"


class TimeOfDay(str, Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"
    UNSPECIFIED = "unspecified"


class RoleType(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    CAMEO = "cameo"


class PropImportance(str, Enum):
    KEY_ITEM = "key_item"
    RECURRING = "recurring"
    ONE_OFF = "one_off"


class ScriptStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    LOCKED = "locked"


class ContinuityCategory(str, Enum):
    CHARACTER_TRAIT = "character_trait"
    RELATIONSHIP = "relationship"
    ITEM_STATE = "item_state"
    LOCATION_STATE = "location_state"
    POWER_LEVEL = "power_level"


class ContinuityScope(str, Enum):
    GLOBAL = "global"
    EPISODE_RANGE = "episode_range"


# ── Bottom-Level Models (Segments) ──


class ScriptSegment(BaseModel):
    """A single segment within a scene — dialogue, narration, action, etc."""

    type: str = Field(description="片段类型: narration/dialogue/action/inner_monologue/voice_over/transition/cliffhanger")
    text: str = Field(description="片段正文内容")
    character_ref: str | None = Field(default=None, description="说话人引用名 (dialogue/inner_monologue 时必填)")
    emotion_tag: str | None = Field(default=None, description="情绪标签, 如 '愤怒' '冷笑' '哽咽'")
    action_tag: str | None = Field(default=None, description="动作标注, 如 '拔剑' '转身' '摔门'")
    duration_hint_ms: int | None = Field(default=None, ge=500, description="预估时长（毫秒）")


class SceneContent(BaseModel):
    """The content of a scene — the core narrative unit."""

    segments: list[ScriptSegment] = Field(default_factory=list, min_length=1, description="片段序列")
    scene_duration_estimate_ms: int | None = Field(default=None, description="场景预估总时长（毫秒）")


# ── Scene-Level Models ──


class SceneLocation(BaseModel):
    """Location information for a scene."""

    name: str = Field(description="地点名称")
    time_of_day: str | None = Field(default=None, description="时间(dawn/morning/noon/afternoon/evening/dusk/night/midnight)")
    weather: str | None = Field(default=None, description="天气")
    mood: str | None = Field(default=None, description="场景情绪基调")
    description: str | None = Field(default=None, max_length=1000, description="地点描述")


class CharacterPresent(BaseModel):
    """A character appearing in a specific scene."""

    character_ref: str = Field(description="角色引用名（Stage 2 会关联到正式角色档案）")
    emotional_state: str | None = Field(default=None, description="本场情绪状态")
    costume_note: str | None = Field(default=None, description="服装备注")
    appearance_note: str | None = Field(default=None, description="本场特殊外貌变化")


class Scene(BaseModel):
    """A single scene within an episode."""

    scene_id: str = Field(default="", description="场景 ID, 如 SC-E001-S003")
    scene_index: int = Field(ge=1, description="场景序号")
    location: SceneLocation = Field(description="场景地点信息")
    characters_present: list[CharacterPresent] = Field(default_factory=list, description="出场角色")
    content: SceneContent = Field(description="场景内容")
    props_mentioned: list[str] = Field(default_factory=list, description="涉及的道具名称")
    visual_emphasis: list[str] = Field(default_factory=list, description="需要视觉强调的元素")


# ── Episode ──


class Episode(BaseModel):
    """A single episode of the comic drama."""

    episode_index: int = Field(ge=1, description="集序号")
    title: str = Field(max_length=200, description="本集标题")
    hook: str | None = Field(default=None, max_length=500, description="开头钩子——吸引观众的悬念")
    cliffhanger: str | None = Field(default=None, max_length=500, description="结尾悬念——留钩子")
    summary: str | None = Field(default=None, max_length=1000, description="本集概要")
    scenes: list[Scene] = Field(default_factory=list, min_length=1, description="场景序列")


# ── Global Context ──


class StoryWorld(BaseModel):
    """World-building context shared across all episodes."""

    setting: str = Field(default="", description="世界观设定描述")
    era: str = Field(default="", description="时代背景")
    rules: list[str] = Field(default_factory=list, description="世界观规则列表")


class PowerSystem(BaseModel):
    """Power/magic/cultivation system (especially important for xianxia/wuxia)."""

    name: str = Field(default="", description="力量体系名称")
    levels: list[str] = Field(default_factory=list, description="等级序列")
    rules: str = Field(default="", description="力量规则说明")


class TimelineEvent(BaseModel):
    """A key event on the story timeline."""

    event_id: str = Field(default="", description="事件 ID")
    description: str = Field(default="", description="事件描述")
    episode_ref: int | None = Field(default=None, description="关联集数")
    is_major: bool = Field(default=False, description="是否为核心事件")


class ContinuityRule(BaseModel):
    """A continuity constraint that spans episodes."""

    rule_id: str = Field(default="", description="规则 ID")
    category: ContinuityCategory = Field(description="规则类别")
    description: str = Field(default="", description="规则描述")
    scope: ContinuityScope = Field(default=ContinuityScope.GLOBAL, description="适用范围")
    episode_range: list[int] = Field(default_factory=list, description="适用集数范围")


class GlobalContext(BaseModel):
    """Global narrative context — shared across all episodes."""

    story_world: StoryWorld = Field(default_factory=StoryWorld, description="世界观")
    power_system: PowerSystem = Field(default_factory=PowerSystem, description="力量体系")
    timeline: list[dict] = Field(default_factory=list, description="关键事件时间线")
    continuity_rules: list[dict] = Field(default_factory=list, description="连续性规则")


# ── Indexes (auto-computed from episodes) ──


class CharacterRelationship(BaseModel):
    """A relationship between two characters."""

    with_character: str = Field(description="对方角色引用名")
    relationship_type: str = Field(description="关系类型, 如 '师徒' '恋人' '仇敌'")


class CharacterIndexEntry(BaseModel):
    """A character summary in the script-level character index.

    Populated by the Writer Agent; used as input for Stage 2 character design.
    """

    ref_name: str = Field(description="角色引用名 (与 scene 中 character_ref 对应)")
    full_name: str | None = Field(default=None, description="全名")
    role_type: RoleType = Field(description="角色类型")
    scene_count: int = Field(default=0, ge=0, description="出场场景数")
    dialogue_count: int = Field(default=0, ge=0, description="对白段数")
    first_episode: int = Field(default=1, ge=1, description="首次出场集数")
    traits_from_script: list[str] = Field(default_factory=list, description="从剧本中提取的性格特征")
    relationships: list[CharacterRelationship] = Field(default_factory=list, description="角色关系列表")


class LocationIndexEntry(BaseModel):
    """A location summary in the script-level location index."""

    name: str = Field(description="地点名称")
    scene_count: int = Field(default=0, ge=0, description="出现场景数")
    variations: list[str] = Field(default_factory=list, description="不同时间/天气的变体")


class PropIndexEntry(BaseModel):
    """A prop summary in the script-level prop index."""

    name: str = Field(description="道具名称")
    scene_count: int = Field(default=0, ge=0, description="出现场景数")
    importance: PropImportance = Field(default=PropImportance.ONE_OFF, description="重要程度")
    description_from_script: str = Field(default="", description="剧本中的道具描述")


# ── Review History ──


class ReviewHistoryEntry(BaseModel):
    """A single review round record."""

    round: int = Field(ge=1, description="审查轮次")
    reviewer: str = Field(description="审查者: drama_critic_agent | style_agent | human")
    verdict: str = Field(description="审查结论: approved | needs_revision | rejected")
    comments: str = Field(default="", description="审查意见")
    resolved: bool = Field(default=False, description="问题是否已解决")


# ── Top-Level: StructuredScript ──


class StructuredScript(BaseModel):
    """Stage 1 complete output — the single source of truth for the script.

    This is the data contract between Stage 1 → Stage 2.
    All fields match docs/schema-design.md §Stage 1 Output Schema.
    """

    script_id: str = Field(default="", description="剧本唯一 ID (后处理自动注入)")
    project_id: str = Field(default="", description="关联项目 ID")
    version: int = Field(default=1, ge=1, description="版本号")
    created_at: str = Field(default="", description="创建时间 ISO 8601")
    updated_at: str = Field(default="", description="更新时间 ISO 8601")
    status: ScriptStatus = Field(default=ScriptStatus.DRAFT, description="剧本状态")

    # Core content
    global_context: GlobalContext = Field(default_factory=GlobalContext, description="全局语境")
    episodes: list[Episode] = Field(
        default_factory=list, min_length=1, max_length=200, description="分集剧本"
    )

    # Auto-computed indexes (may be empty from LLM, filled by post-processing)
    character_index: list[CharacterIndexEntry] = Field(default_factory=list, description="角色索引")
    location_index: list[LocationIndexEntry] = Field(default_factory=list, description="场景索引")
    prop_index: list[PropIndexEntry] = Field(default_factory=list, description="道具索引")

    # Audit trail
    review_history: list[ReviewHistoryEntry] = Field(default_factory=list, description="审查记录")

    @model_validator(mode="after")
    def _validate_episode_indices(self) -> "StructuredScript":
        """Ensure episode indices are sequential starting from 1."""
        for i, ep in enumerate(self.episodes, start=1):
            if ep.episode_index != i:
                # Auto-correct rather than reject — LLMs may produce wrong indices
                ep.episode_index = i
        return self

    def stamp(self, project_id: str, script_id: str) -> None:
        """Inject server-side metadata after LLM generation."""
        now = datetime.now(timezone.utc).isoformat()
        self.script_id = script_id
        self.project_id = project_id
        self.created_at = now
        self.updated_at = now

    def summary(self) -> dict:
        """Return a lightweight summary for dashboards."""
        total_scenes = sum(len(ep.scenes) for ep in self.episodes)
        total_segments = sum(
            len(scene.content.segments) for ep in self.episodes for scene in ep.scenes
        )
        return {
            "script_id": self.script_id,
            "version": self.version,
            "status": self.status.value,
            "episode_count": len(self.episodes),
            "scene_count": total_scenes,
            "segment_count": total_segments,
            "character_count": len(self.character_index),
            "location_count": len(self.location_index),
            "prop_count": len(self.prop_index),
        }
