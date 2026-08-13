"""ShotComposer Agent — translates script + assets into detailed shot plan."""

from typing import Any

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, ReviewRecord, Verdict,
)
from app.utils.id_generator import generate_shot_id, generate_storyboard_id
from app.utils.seed_manager import SeedManager


def build_shot_composer_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="shot_composer_v1",
            identity="分镜导演",
            expertise=["镜头语言", "构图设计", "景别选择", "运镜设计", "转场", "漫剧分镜"],
            personality="每一个镜头都服务于叙事——不炫技，只选择最合适的表达方式",
            blind_spots=["可能过于保守地使用固定机位", "对极度实验性的角度持保留态度"],
            quality_bias="更关注叙事清晰度而非视觉华丽度",
        ),
        scope=AgentScope(
            stage="storyboard",
            reads=["structured_script", "asset_profiles", "target_spec"],
            writes=["shot_plan"],
            must_not_modify=["structured_script", "asset_profiles"],
        ),
        role=AgentRole.AUTHOR,
        can_be_reviewed_by=["pacing_director_v1", "continuity_check_v1"],
    )


class ShotComposerAgent(BaseAgent):
    """Translates script scenes into detailed shot specifications.

    For each scene in the script, generates:
    - Shot breakdown (shot_type, camera_angle, camera_movement)
    - Composition (subject_focus, foreground/midground/background, characters_in_frame)
    - image_prompt (positive + negative + seed + model_params)
    - video_prompt (if motion is specified)
    - dialogue mapping (character_id, text, start_ms, end_ms)
    - Transition from previous shot
    - VFX and audio notes
    """

    def __init__(self, llm_service: Any = None):
        super().__init__(build_shot_composer_config())
        self.seed_manager: SeedManager | None = None
        self.llm_service = llm_service

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate a complete shot plan from script and assets.

        Args:
            input_data: {
                project_id, script: {episodes},
                assets: {style_manifest, characters, locations, props},
                target_spec: {episode_duration_seconds, aspect_ratio},
                continuity_rules: list
            }
        """
        project_id = input_data.get("project_id", "")
        script = input_data.get("script", {})
        assets = input_data.get("assets", {})
        target_spec = input_data.get("target_spec", {})

        # Initialize seed manager from style manifest
        global_seed = assets.get("style_manifest", {}).get("global_style_seed", 42)
        self.seed_manager = SeedManager(global_seed)

        # Index assets by id for quick lookup
        char_map = {c["ref_name"]: c for c in assets.get("characters", [])}
        loc_map = {l["name"]: l for l in assets.get("locations", [])}
        prop_map = {p["name"]: p for p in assets.get("props", [])}

        episodes = []
        for ep_data in script.get("episodes", []):
            ep_idx = ep_data.get("episode_index", 1)
            ep_shots = self._compose_episode(
                episode_data=ep_data,
                char_map=char_map,
                loc_map=loc_map,
                prop_map=prop_map,
                target_spec=target_spec,
            )
            episodes.append(ep_shots)

        # Calculate totals
        total_shots = sum(ep.get("episode_shot_count", 0) for ep in episodes)
        total_duration = sum(ep.get("episode_total_duration_ms", 0) for ep in episodes)

        return {
            "storyboard_id": generate_storyboard_id(),
            "project_id": project_id,
            "script_id": script.get("script_id", ""),
            "asset_set_id": assets.get("asset_set_id", ""),
            "version": 1,
            "status": "draft",
            "episodes": episodes,
            "tempo_analysis": self._analyze_tempo(episodes),
            "review_history": [],
        }

    def _compose_episode(
        self,
        episode_data: dict,
        char_map: dict,
        loc_map: dict,
        prop_map: dict,
        target_spec: dict,
    ) -> dict:
        """Compose one episode into shots."""
        ep_idx = episode_data.get("episode_index", 1)
        target_duration_ms = target_spec.get("episode_duration_seconds", 120) * 1000

        scenes = []
        total_shot_idx = 0
        ep_duration = 0

        for scene_data in episode_data.get("scenes", []):
            scene_shots = self._compose_scene(
                episode_index=ep_idx,
                scene_data=scene_data,
                starting_shot_idx=total_shot_idx + 1,
                char_map=char_map,
                loc_map=loc_map,
                prop_map=prop_map,
            )

            total_shot_idx += scene_shots["scene_shot_count"]
            ep_duration += scene_shots["scene_total_duration_ms"]
            scenes.append(scene_shots)

        return {
            "episode_index": ep_idx,
            "title": episode_data.get("title", ""),
            "estimated_duration_ms": ep_duration,
            "scenes": scenes,
            "episode_total_duration_ms": ep_duration,
            "episode_shot_count": total_shot_idx,
        }

    def _compose_scene(
        self,
        episode_index: int,
        scene_data: dict,
        starting_shot_idx: int,
        char_map: dict,
        loc_map: dict,
        prop_map: dict,
    ) -> dict:
        """Break one scene into shots.

        Rules:
        - Dialogue-heavy scenes: alternating medium_close_up shots (正反打)
        - Action scenes: varied angles + shorter duration
        - Establishing shots: wide/long at scene start
        - Emotional peaks: close_up
        """
        scene_id = scene_data.get("scene_id", "")
        scene_idx = scene_data.get("scene_index", 1)
        location = scene_data.get("location", {})
        characters_present = scene_data.get("characters_present", [])
        segments = scene_data.get("content", {}).get("segments", [])
        visual_emphasis = scene_data.get("visual_emphasis", [])

        loc_name = location.get("name", "")
        loc = loc_map.get(loc_name, {})

        shots = []
        shot_idx = starting_shot_idx

        # 1. Establishing shot (if scene has a named location)
        if loc_name:
            shots.append(self._create_shot(
                episode_index=episode_index,
                scene_index=scene_idx,
                shot_index=shot_idx,
                shot_type="long_shot",
                camera_angle="eye_level",
                camera_movement={"type": "static"},
                duration_ms=2000,  # 2s establishing
                location=loc,
                characters=[],
                dialogue=[],
                transition="fade_in" if shot_idx == 1 else "cut",
                mood=location.get("mood", ""),
            ))
            shot_idx += 1

        # 2. Map segments to shots
        for seg in segments:
            seg_type = seg.get("type", "narration")
            text = seg.get("text", "")
            action = seg.get("action_tag", "")
            emotion = seg.get("emotion_tag", "")
            char_ref = seg.get("character_ref", "")
            duration_hint = seg.get("duration_hint_ms", 3000)

            if seg_type == "dialogue":
                # Check if previous shot was same character for reverse-angle
                prev_char = shots[-1]["characters_in_frame"][0]["character_id"] if shots and shots[-1]["characters_in_frame"] else None
                current_char = char_map.get(char_ref, {})

                shot_type = "over_shoulder" if prev_char else "medium_close_up"
                angle = "eye_level"
                if emotion == "愤怒" or emotion == "威胁":
                    angle = "low_angle"
                elif emotion == "悲伤" or emotion == "无助":
                    angle = "high_angle"

                shots.append(self._create_shot(
                    episode_index=episode_index,
                    scene_index=scene_idx,
                    shot_index=shot_idx,
                    shot_type=shot_type,
                    camera_angle=angle,
                    camera_movement={"type": "static"},
                    duration_ms=duration_hint,
                    location=loc,
                    characters=[self._char_in_frame(char_map.get(char_ref, {}), emotion)],
                    dialogue=[{
                        "character_id": char_map.get(char_ref, {}).get("character_id", ""),
                        "text": text,
                        "start_ms": 0,
                        "end_ms": duration_hint,
                        "emotion": emotion or "",
                        "delivery_notes": "",
                    }],
                    transition="cut",
                    mood=location.get("mood", ""),
                ))
                shot_idx += 1

            elif seg_type == "action":
                # Action segments → dynamic shots
                movement = "static"
                if action and any(w in action for w in ["拔", "打", "跑", "飞"]):
                    movement = "track_right"

                shots.append(self._create_shot(
                    episode_index=episode_index,
                    scene_index=scene_idx,
                    shot_index=shot_idx,
                    shot_type="full_shot",
                    camera_angle="eye_level",
                    camera_movement={"type": movement, "intensity": "moderate"},
                    duration_ms=duration_hint,
                    location=loc,
                    characters=[
                        self._char_in_frame(char_map.get(c.get("character_ref", "")), "")
                        for c in characters_present
                    ],
                    dialogue=[],
                    transition="cut",
                    mood=location.get("mood", ""),
                    action_tag=action,
                ))
                shot_idx += 1

            elif seg_type == "narration" or seg_type == "voice_over":
                # Narration → wide atmospheric shots
                shots.append(self._create_shot(
                    episode_index=episode_index,
                    scene_index=scene_idx,
                    shot_index=shot_idx,
                    shot_type="long_shot",
                    camera_angle="eye_level",
                    camera_movement={"type": "pan_right", "intensity": "subtle"},
                    duration_ms=duration_hint,
                    location=loc,
                    characters=[],
                    dialogue=[],
                    transition="cut",
                    mood=location.get("mood", ""),
                ))
                shot_idx += 1

            elif seg_type == "inner_monologue":
                # Inner monologue → close_up on the thinking character
                thinker = char_map.get(char_ref, {})
                shots.append(self._create_shot(
                    episode_index=episode_index,
                    scene_index=scene_idx,
                    shot_index=shot_idx,
                    shot_type="close_up",
                    camera_angle="eye_level",
                    camera_movement={"type": "zoom_in", "intensity": "subtle"},
                    duration_ms=duration_hint,
                    location=loc,
                    characters=[self._char_in_frame(thinker, emotion or "沉思")],
                    dialogue=[],
                    transition="cut",
                    mood="introspective",
                ))
                shot_idx += 1

            elif seg_type == "transition":
                # Scene transition marker — use wide establishing for next scene
                pass

        scene_duration = sum(s["duration_ms"] for s in shots)

        return {
            "scene_id": scene_id,
            "location_id": loc.get("location_id", ""),
            "scene_mood": location.get("mood", ""),
            "shots": shots,
            "scene_shot_count": len(shots),
            "scene_total_duration_ms": scene_duration,
        }

    def _create_shot(
        self,
        episode_index: int,
        scene_index: int,
        shot_index: int,
        shot_type: str,
        camera_angle: str,
        camera_movement: dict,
        duration_ms: int,
        location: dict,
        characters: list,
        dialogue: list,
        transition: str,
        mood: str,
        action_tag: str = "",
    ) -> dict:
        """Create a single shot with all required fields."""
        shot_id = generate_shot_id(episode_index, scene_index, shot_index)

        # Generate seed for this shot
        seed = self.seed_manager.shot_seed(episode_index, scene_index, shot_index) if self.seed_manager else 42

        # Build image prompt by combining character + location templates
        char_prompts = " ".join(c.get("prompt_fragment", "") for c in characters if c)
        loc_prompt = location.get("location_prompt_template", "")

        positive_prompt = f"{shot_type} shot, {camera_angle} angle, "
        if char_prompts:
            positive_prompt += f"{char_prompts}, "
        if loc_prompt:
            positive_prompt += f"{loc_prompt}, "
        positive_prompt += f"{mood} atmosphere, cinematic lighting, 16:9 aspect ratio"

        negative_prompt = "blurry, low quality, deformed, watermark, text, extra limbs"

        return {
            "shot_id": shot_id,
            "shot_index": shot_index,
            "shot_type": shot_type,
            "camera_angle": camera_angle,
            "camera_movement": camera_movement,
            "duration_ms": duration_ms,
            "keyframe": {
                "composition": {
                    "subject_focus": characters[0].get("character_id", location.get("name", "")) if characters else location.get("name", ""),
                    "foreground": "",
                    "midground": "",
                    "background": location.get("name", ""),
                    "depth_of_field": "shallow" if shot_type in ("close_up", "extreme_close_up") else "medium",
                    "rule_of_thirds_position": "center" if shot_type == "close_up" else "left_third",
                },
                "characters_in_frame": characters,
                "props_in_frame": [],
                "image_prompt": {
                    "positive": positive_prompt,
                    "negative": negative_prompt,
                    "seed": seed,
                    "model_params": {
                        "cfg_scale": 7.0,
                        "steps": 30,
                        "width": 1920,
                        "height": 1080,
                    },
                },
                "video_prompt": {
                    "start_frame_prompt": positive_prompt,
                    "end_frame_prompt": positive_prompt,
                    "motion_description": f"{camera_movement.get('type', 'static')} camera movement",
                    "motion_strength": 0.3 if camera_movement.get("type") == "static" else 0.7,
                },
            },
            "dialogue": dialogue,
            "audio_notes": {
                "bgm": "",
                "sfx": [],
                "ambient": f"{location.get('name', '')} 环境音",
            },
            "transition": {"from_previous": transition, "transition_duration_ms": 500, "transition_notes": ""},
            "vfx_notes": [],
            "reference_shot_ids": [],
        }

    def _char_in_frame(self, char: dict, emotion: str) -> dict:
        """Build character-in-frame data."""
        if not char:
            return {}
        costumes = char.get("design_sheet", {}).get("costumes", [])
        default_costume = costumes[0] if costumes else {}
        return {
            "character_id": char.get("character_id", ""),
            "costume_id": default_costume.get("costume_id", ""),
            "pose": "standing",
            "expression": emotion or "neutral",
            "position_in_frame": "center",
            "action": "",
            "prompt_fragment": char.get("character_prompt_template", ""),
        }

    def _analyze_tempo(self, episodes: list) -> dict:
        """Analyze shot duration distribution for pacing insights."""
        all_durations = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for shot in scene.get("shots", []):
                    all_durations.append(shot.get("duration_ms", 0))

        if not all_durations:
            return {"shot_duration_distribution": {}, "pacing_curve": [], "warnings": []}

        dist = {
            "ultra_short_count": sum(1 for d in all_durations if d < 1000),
            "short_count": sum(1 for d in all_durations if 1000 <= d < 2000),
            "medium_count": sum(1 for d in all_durations if 2000 <= d < 5000),
            "long_count": sum(1 for d in all_durations if 5000 <= d < 10000),
            "ultra_long_count": sum(1 for d in all_durations if d >= 10000),
        }

        warnings = []
        if dist["medium_count"] / max(len(all_durations), 1) > 0.7:
            warnings.append({
                "severity": "warning",
                "message": "超过70%的镜头时长在2-5秒，节奏可能偏平",
            })

        return {
            "shot_duration_distribution": dist,
            "pacing_curve": [],
            "warnings": warnings,
        }

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise shot plan based on review feedback."""
        revised = dict(original_output)
        revised["version"] = original_output.get("version", 1) + 1

        blockers = [i for i in feedback.critical_issues if i.severity == IssueSeverity.BLOCKER]
        if blockers:
            return {"status": "escalated", "blockers": [b.model_dump() for b in blockers], **revised}

        self.record_review(ReviewRecord(
            round=len(self.review_history) + 1,
            timestamp="",
            reviewer={"agent_id": "pacing_director_v1", "agent_version": "1.0"},
            verdict=feedback.overall_verdict,
            total_score=feedback.total_score,
            dimension_scores=feedback.dimension_scores,
            issues=[i.model_dump() for i in feedback.critical_issues],
        ))

        return revised
