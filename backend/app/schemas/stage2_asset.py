"""Stage 2 — AssetProfiles Pydantic models for LLM structured output.

Mirrors docs/schema-design.md §Stage 2 Output Schema.
Used with LLM.with_structured_output() for character/scene/prop design generation.
"""

from typing import Literal

from pydantic import BaseModel, Field


class FaceDesign(BaseModel):
    shape: str = Field(default="", description="脸型")
    eyes: str = Field(default="", description="眼型")
    nose: str = Field(default="", description="鼻型")
    mouth: str = Field(default="", description="嘴型")
    skin_tone: str = Field(default="", description="肤色")
    overall_description: str = Field(default="", description="整体面部描述")


class HairDesign(BaseModel):
    color: str = Field(default="", description="发色")
    style: str = Field(default="", description="发型")
    length: str = Field(default="", description="发长")


class Appearance(BaseModel):
    age_appearance: str = Field(default="", description="视觉年龄范围")
    gender: str = Field(default="", description="性别")
    body_type: str = Field(default="", description="体型")
    height_cm: int | None = Field(default=None, description="身高cm")
    face: FaceDesign = Field(default_factory=FaceDesign)
    hair: HairDesign = Field(default_factory=HairDesign)
    distinguishing_features: list[str] = Field(default_factory=list, description="识别特征")


class Costume(BaseModel):
    costume_id: str = Field(default="", description="服装ID")
    name: str = Field(default="", description="服装名称")
    description: str = Field(default="", description="服装描述")
    scenes_used_in: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)


class Expressions(BaseModel):
    neutral: str = Field(default="", description="默认表情")
    happy: str = ""
    angry: str = ""
    sad: str = ""
    surprised: str = ""
    scheming: str = ""
    cold: str = ""


class DesignSheet(BaseModel):
    appearance: Appearance = Field(default_factory=Appearance)
    costumes: list[Costume] = Field(default_factory=list, min_length=1)
    expressions: Expressions = Field(default_factory=Expressions)
    pose_notes: str = Field(default="", description="体态特征")


class CharacterAsset(BaseModel):
    character_id: str = Field(default="", description="CHAR-0001格式")
    ref_name: str = Field(description="与剧本character_ref对应")
    full_name: str | None = None
    role_type: Literal["protagonist", "antagonist", "supporting", "cameo"] = "supporting"
    design_sheet: DesignSheet = Field(default_factory=DesignSheet)
    character_prompt_template: str = Field(default="", max_length=3000, description="稳定生图提示词模板")
    voice_profile: dict = Field(default_factory=dict)


class LocationVariation(BaseModel):
    variation_id: str = ""
    condition: str = Field(description="条件如night/rain/destroyed")
    description_modifier: str = ""


class LocationDesign(BaseModel):
    description: str = Field(default="", description="场景空间描述")
    key_features: list[str] = Field(default_factory=list)
    layout_notes: str = ""
    variations: list[LocationVariation] = Field(default_factory=list)


class LocationAsset(BaseModel):
    location_id: str = Field(default="", description="LOC-0001格式")
    name: str = Field(description="场景名称")
    design_sheet: LocationDesign = Field(default_factory=LocationDesign)
    location_prompt_template: str = Field(default="", max_length=3000, description="场景生图提示词模板")


class PropDesign(BaseModel):
    description: str = ""
    material: str = ""
    color: str = ""
    size_hint: str = ""
    special_effects: str = ""


class PropAsset(BaseModel):
    prop_id: str = Field(default="", description="PROP-0001格式")
    name: str = Field(description="道具名称")
    importance: Literal["key_item", "recurring", "one_off"] = "one_off"
    design: PropDesign = Field(default_factory=PropDesign)
    prop_prompt_template: str = Field(default="", max_length=2000)


class ColorPalette(BaseModel):
    name: str = ""
    primary_colors: list[str] = Field(default_factory=list, max_length=5)
    accent_colors: list[str] = Field(default_factory=list, max_length=3)


class StyleManifest(BaseModel):
    art_style: str = Field(default="anime", description="美术风格")
    global_style_seed: int = Field(default=42, description="全局视觉种子")
    color_palette: ColorPalette = Field(default_factory=ColorPalette)
    line_style: Literal["clean", "sketchy", "bold", "delicate", "none"] = "clean"
    lighting_default: str = ""
    global_negative_prompt: str = Field(default="", max_length=2000)


class AssetProfiles(BaseModel):
    """Stage 2 complete output — character/scene/prop design profiles."""
    asset_set_id: str = ""
    project_id: str = ""
    script_id: str = ""
    version: int = Field(default=1, ge=1)
    status: Literal["draft", "review", "approved", "locked"] = "draft"
    style_manifest: StyleManifest = Field(default_factory=StyleManifest)
    characters: list[CharacterAsset] = Field(default_factory=list, min_length=1)
    locations: list[LocationAsset] = Field(default_factory=list, min_length=1)
    props: list[PropAsset] = Field(default_factory=list)
    review_history: list[dict] = Field(default_factory=list)
