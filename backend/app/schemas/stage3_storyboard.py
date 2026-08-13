"""Stage 3 — ShotPlan Pydantic models for LLM structured output.

Mirrors docs/schema-design.md §Stage 3 Output Schema.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CharacterInFrame(BaseModel):
    character_id: str = Field(description="角色ID")
    costume_id: str = Field(default="", description="服装ID")
    pose: str = ""
    expression: str = ""
    position_in_frame: str = ""
    action: str = ""


class PropInFrame(BaseModel):
    prop_id: str = ""
    position_in_frame: str = ""
    state: str = ""


class Composition(BaseModel):
    subject_focus: str = Field(description="画面焦点")
    foreground: str = ""
    midground: str = ""
    background: str = ""
    depth_of_field: Literal["shallow", "medium", "deep"] = "medium"


class ImagePrompt(BaseModel):
    positive: str = Field(max_length=4000, description="正向提示词(英文)")
    negative: str = Field(default="", max_length=2000, description="负向提示词")
    seed: int = Field(default=42, description="种子值")


class Keyframe(BaseModel):
    composition: Composition = Field(default_factory=Composition)
    characters_in_frame: list[CharacterInFrame] = Field(default_factory=list)
    props_in_frame: list[PropInFrame] = Field(default_factory=list)
    image_prompt: ImagePrompt = Field(description="生图提示词")


class Dialogue(BaseModel):
    character_id: str = Field(description="说话角色")
    text: str = Field(description="对白文本")
    start_ms: int = Field(ge=0, description="开始毫秒")
    end_ms: int = Field(ge=0, description="结束毫秒")
    emotion: str = ""
    delivery_notes: str = ""


class CameraMovement(BaseModel):
    type: Literal["static", "pan_left", "pan_right", "tilt_up", "tilt_down",
                   "zoom_in", "zoom_out", "dolly_in", "dolly_out",
                   "track_left", "track_right", "arc", "handheld"] = "static"
    intensity: Literal["subtle", "moderate", "dramatic"] = "subtle"


class Transition(BaseModel):
    from_previous: Literal["cut", "fade_in", "fade_out", "crossfade",
                            "wipe_left", "wipe_right", "slide", "zoom_transition", "none"] = "cut"
    transition_duration_ms: int = 0


class Shot(BaseModel):
    shot_id: str = Field(default="", description="SH-E001-S001-001格式")
    shot_index: int = Field(ge=1)
    shot_type: Literal["extreme_close_up", "close_up", "medium_close_up",
                        "medium_shot", "medium_full_shot", "full_shot",
                        "long_shot", "extreme_long_shot", "over_shoulder",
                        "pov", "dutch_angle", "aerial"] = "medium_shot"
    camera_angle: Literal["eye_level", "low_angle", "high_angle",
                           "birds_eye", "worms_eye", "dutch"] = "eye_level"
    camera_movement: CameraMovement = Field(default_factory=CameraMovement)
    duration_ms: int = Field(ge=500, le=30000, description="镜头时长毫秒")
    keyframe: Keyframe = Field(description="关键帧定义")
    dialogue: list[Dialogue] = Field(default_factory=list)
    transition: Transition = Field(default_factory=Transition)


class SceneShot(BaseModel):
    scene_id: str = Field(description="场景ID")
    location_id: str = ""
    scene_mood: str = ""
    shots: list[Shot] = Field(default_factory=list, min_length=1)


class EpisodeShot(BaseModel):
    episode_index: int = Field(ge=1)
    title: str = ""
    estimated_duration_ms: int = 0
    scenes: list[SceneShot] = Field(default_factory=list, min_length=1)


class ShotPlan(BaseModel):
    """Stage 3 complete output — shot-by-shot storyboard with keyframe prompts."""
    storyboard_id: str = ""
    project_id: str = ""
    script_id: str = ""
    asset_set_id: str = ""
    version: int = Field(default=1, ge=1)
    status: Literal["draft", "review", "approved", "locked"] = "draft"
    episodes: list[EpisodeShot] = Field(default_factory=list, min_length=1)
    review_history: list[dict] = Field(default_factory=list)
