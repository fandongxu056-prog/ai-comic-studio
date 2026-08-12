"""Integration tests for Stage 1 — LLM-powered script generation and review.

Uses mock LLM service to test the full generate-review-revise cycle
without requiring real API calls.

Run with: pytest tests/test_stage1_llm.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.stage1_script.critic import DramaCriticAgent
from app.agents.stage1_script.style_guard import StyleGuardAgent
from app.agents.stage1_script.writer import ScriptWriterAgent
from app.schemas.stage1_script import (
    CharacterIndexEntry,
    CharacterPresent,
    Episode,
    GlobalContext,
    LocationIndexEntry,
    PropIndexEntry,
    RoleType,
    Scene,
    SceneContent,
    SceneLocation,
    ScriptSegment,
    SegmentType,
    StoryWorld,
    StructuredScript,
)


# ── Test Fixtures ──


def make_sample_script() -> dict:
    """Build a minimal but valid structured script for testing."""
    script = StructuredScript(
        project_id="PRJ-TEST001",
        script_id="SCR-TEST001",
        version=1,
        status="draft",
        global_context=GlobalContext(
            story_world=StoryWorld(
                setting="现代都市",
                era="2024年",
                rules=["普通人不知道灵气的存在"],
            ),
        ),
        episodes=[
            Episode(
                episode_index=1,
                title="觉醒",
                hook="一个普通上班族在地铁站突然看到了不该看到的东西",
                cliffhanger="当他打开那扇门的瞬间，整个世界安静了...",
                summary="主角李凡意外发现灵气复苏的秘密",
                scenes=[
                    Scene(
                        scene_id="SC-E001-S001",
                        scene_index=1,
                        location=SceneLocation(
                            name="地铁站",
                            time_of_day="evening",
                            mood="日常",
                        ),
                        characters_present=[
                            CharacterPresent(
                                character_ref="李凡",
                                emotional_state="疲惫",
                            ),
                        ],
                        content=SceneContent(
                            segments=[
                                ScriptSegment(
                                    type=SegmentType.NARRATION,
                                    text="傍晚六点半的地铁站，人流如织。",
                                ),
                                ScriptSegment(
                                    type=SegmentType.ACTION,
                                    text="李凡拖着一身疲惫挤下地铁",
                                    action_tag="擦汗",
                                ),
                                ScriptSegment(
                                    type=SegmentType.DIALOGUE,
                                    character_ref="李凡",
                                    text="终于下班了...今天又要加班到几点呢",
                                    emotion_tag="疲惫",
                                ),
                                ScriptSegment(
                                    type=SegmentType.NARRATION,
                                    text="突然，他在人群中看到了一团不该存在的黑色雾气。",
                                ),
                                ScriptSegment(
                                    type=SegmentType.ACTION,
                                    text="李凡猛地睁大眼睛，停下脚步",
                                    emotion_tag="震惊",
                                    action_tag="停顿",
                                ),
                            ],
                        ),
                        props_mentioned=["手机"],
                        visual_emphasis=["黑色雾气", "李凡的表情变化"],
                    ),
                    Scene(
                        scene_id="SC-E001-S002",
                        scene_index=2,
                        location=SceneLocation(
                            name="神秘房间",
                            time_of_day="night",
                            mood="神秘",
                        ),
                        characters_present=[
                            CharacterPresent(
                                character_ref="李凡",
                                emotional_state="恐惧",
                            ),
                            CharacterPresent(
                                character_ref="神秘老者",
                                emotional_state="冷静",
                            ),
                        ],
                        content=SceneContent(
                            segments=[
                                ScriptSegment(
                                    type=SegmentType.DIALOGUE,
                                    character_ref="神秘老者",
                                    text="你终于来了。我们等了很久。",
                                    emotion_tag="冷静",
                                ),
                                ScriptSegment(
                                    type=SegmentType.DIALOGUE,
                                    character_ref="李凡",
                                    text="你是谁？这是什么地方？",
                                    emotion_tag="恐惧",
                                    action_tag="后退一步",
                                ),
                                ScriptSegment(
                                    type=SegmentType.NARRATION,
                                    text="老人的眼中闪过一丝金光。",
                                ),
                                ScriptSegment(
                                    type=SegmentType.DIALOGUE,
                                    character_ref="神秘老者",
                                    text="这个世界，不是你以为的那样。灵气正在复苏，而你——是命定之人。",
                                    emotion_tag="庄重",
                                ),
                            ],
                        ),
                        props_mentioned=["古书", "水晶球"],
                        visual_emphasis=["老人眼中的金光", "房间内的符文"],
                    ),
                ],
            ),
        ],
        character_index=[
            CharacterIndexEntry(
                ref_name="李凡",
                full_name="李凡",
                role_type=RoleType.PROTAGONIST,
                scene_count=2,
                dialogue_count=3,
                first_episode=1,
                traits_from_script=["疲惫的上班族", "觉醒者"],
            ),
            CharacterIndexEntry(
                ref_name="神秘老者",
                role_type=RoleType.SUPPORTING,
                scene_count=1,
                dialogue_count=2,
                first_episode=1,
                traits_from_script=["引路人", "知情者"],
            ),
        ],
        location_index=[
            LocationIndexEntry(name="地铁站", scene_count=1, variations=["evening/"]),
            LocationIndexEntry(name="神秘房间", scene_count=1, variations=["night/"]),
        ],
        prop_index=[
            PropIndexEntry(name="手机", scene_count=1, importance="one_off"),
            PropIndexEntry(name="古书", scene_count=1, importance="key_item"),
            PropIndexEntry(name="水晶球", scene_count=1, importance="key_item"),
        ],
    )
    return script.model_dump()


def make_project_input() -> dict:
    """Build a realistic project input."""
    return {
        "project_id": "PRJ-TEST001",
        "source_material": {
            "type": "original_idea",
            "raw_text": "一个关于现代都市中灵气复苏的故事。主角李凡是一个普通的上班族，某天在地铁站偶遇神秘老者后，发现自己是被选中的'命定之人'。",
            "word_count": 60,
            "extracted_characters": [
                {"name": "李凡", "role_hint": "protagonist"},
                {"name": "神秘老者", "role_hint": "supporting"},
            ],
            "extracted_locations": [
                {"name": "地铁站"},
                {"name": "神秘房间"},
            ],
        },
        "genre": {
            "primary": "urban",
            "sub_tags": ["灵气复苏", "都市异能"],
        },
        "creative_direction": {
            "adaptation_strategy": "original_creation",
            "narrative_tone": "快节奏爽文",
            "key_themes": ["觉醒", "命运", "隐藏世界"],
            "avoid_elements": ["色情", "血腥暴力"],
        },
        "target_spec": {
            "format": "horizontal_standard",
            "aspect_ratio": "16:9",
            "episode_count": 1,
            "duration_per_episode_seconds": 120,
        },
        "style_preference": {
            "art_style": "anime",
            "color_palette": "warm_dark",
        },
    }


# ── Mock LLM Service ──


class MockLLMService:
    """Mock LLM service that returns pre-built structured scripts."""

    def __init__(self, script_to_return: dict | None = None):
        self.script = script_to_return or make_sample_script()
        self.structured_call_count = 0
        self.text_call_count = 0

    async def generate_structured(self, system_prompt: str, human_prompt: str, schema, **kwargs):
        """Return a pre-built StructuredScript."""
        self.structured_call_count += 1
        # Parse the sample dict into the schema type
        if schema == StructuredScript:
            return StructuredScript.model_validate(self.script)
        return schema.model_validate(self.script)

    async def generate_text(self, system_prompt: str, human_prompt: str, **kwargs) -> str:
        """Return mock review feedback as JSON text."""
        self.text_call_count += 1
        return json.dumps({
            "issues": [
                {
                    "severity": "minor",
                    "location": "episode=1, scene=1",
                    "category": "conflict_density",
                    "description": "开场冲突密度略低，可以在第二段增加张力",
                    "evidence": "前3个segment铺垫偏长",
                    "suggestion": "在旁白中提前暗示黑色雾气的危险",
                }
            ],
            "strengths": [
                {"location": "episode=1, scene=2", "aspect": "神秘老者的出场很有气场"},
                {"location": "episode=1, scene=1", "aspect": "日常到异常的转换节奏好"},
            ],
        }, ensure_ascii=False)


# ── Tests: Schema Validation ──


class TestStructuredScriptSchema:
    """Test the Pydantic models for Stage 1 output."""

    def test_valid_script_passes_validation(self):
        """A complete script should validate successfully."""
        script = make_sample_script()
        parsed = StructuredScript.model_validate(script)
        assert parsed.project_id == "PRJ-TEST001"
        assert len(parsed.episodes) == 1
        assert len(parsed.episodes[0].scenes) == 2
        assert len(parsed.character_index) == 2

    def test_missing_required_fields_fails(self):
        """Script with invalid field types should fail validation."""
        with pytest.raises(Exception):
            StructuredScript.model_validate({"project_id": "test", "episodes": "not_a_list"})

    def test_empty_episodes_fails(self):
        """Script with empty episodes list should fail min_length validation."""
        with pytest.raises(Exception):
            StructuredScript.model_validate({"project_id": "test", "episodes": []})

    def test_script_summary(self):
        """Summary method should return correct counts."""
        script = StructuredScript.model_validate(make_sample_script())
        summary = script.summary()
        assert summary["episode_count"] == 1
        assert summary["scene_count"] == 2
        assert summary["character_count"] == 2
        assert summary["location_count"] == 2
        assert summary["prop_count"] == 3
        assert summary["segment_count"] == 9  # 5 + 4

    def test_episode_index_auto_correction(self):
        """Episodes with wrong indices should be auto-corrected."""
        script = StructuredScript.model_validate(make_sample_script())
        script.episodes[0].episode_index = 999
        validated = StructuredScript.model_validate(script.model_dump())
        assert validated.episodes[0].episode_index == 1

    def test_deserialize_and_reserialize(self):
        """Round-trip: model_dump → model_validate should preserve data."""
        original = StructuredScript.model_validate(make_sample_script())
        json_str = json.dumps(original.model_dump(), ensure_ascii=False)
        reloaded = StructuredScript.model_validate(json.loads(json_str))
        assert reloaded.project_id == original.project_id
        assert len(reloaded.episodes) == len(original.episodes)


# ── Tests: Writer Agent ──


class TestScriptWriterAgent:
    """Test the ScriptWriter agent with mock LLM."""

    def test_writer_without_llm_returns_skeleton(self):
        """Writer without LLM service should return a minimal skeleton."""
        writer = ScriptWriterAgent(llm_service=None)
        result = writer._skeleton(make_project_input())
        assert "script_id" in result
        assert "episodes" in result
        assert result["version"] == 1

    @pytest.mark.asyncio
    async def test_writer_with_mock_llm_generates_script(self):
        """Writer with mock LLM should return the mock script post-processed."""
        mock_llm = MockLLMService()
        writer = ScriptWriterAgent(llm_service=mock_llm)

        result = await writer.execute(input_data=make_project_input())

        assert "script_id" in result
        assert result["script_id"].startswith("SCR-")
        assert len(result["episodes"]) == 1
        assert mock_llm.structured_call_count >= 1

    @pytest.mark.asyncio
    async def test_writer_prompt_contains_genre_info(self):
        """System prompt should include genre and target spec."""
        writer = ScriptWriterAgent(llm_service=None)
        prompt = writer._build_system_prompt(
            genre={"primary": "xianxia", "sub_tags": ["重生", "逆袭"]},
            creative={"narrative_tone": "爽文", "adaptation_strategy": "original_creation", "key_themes": [], "avoid_elements": []},
            target={"episode_count": 3, "duration_per_episode_seconds": 180},
        )
        assert "xianxia" in prompt
        assert "重生" in prompt
        assert "3 集" in prompt
        assert "180 秒" in prompt

    def test_writer_skeleton_has_valid_structure(self):
        """Skeleton output should be a valid StructuredScript with placeholder data."""
        writer = ScriptWriterAgent(llm_service=None)
        result = writer._skeleton(make_project_input())
        # Should be deserializable and have 1 episode
        parsed = StructuredScript.model_validate(result)
        assert parsed.project_id == "PRJ-TEST001"
        assert len(parsed.episodes) == 1
        assert len(parsed.episodes[0].scenes) == 1


# ── Tests: Critic Agent ──


class TestDramaCriticAgent:
    """Test the DramaCritic agent's heuristic checks."""

    def test_critic_detects_empty_episode(self):
        """Critic should flag episodes with no scenes."""
        critic = DramaCriticAgent()
        issues = critic._check_structure([])
        assert len(issues) == 0  # No episodes = no issues

        issues = critic._check_structure([{"episode_index": 1, "scenes": []}])
        assert len(issues) == 1
        assert issues[0].severity.value == "blocker"

    def test_critic_detects_missing_hook(self):
        """Critic should flag episodes without an effective hook."""
        critic = DramaCriticAgent()
        ep = {
            "episode_index": 1,
            "scenes": [{
                "scene_id": "SC-E001-S001",
                "scene_index": 1,
                "content": {
                    "segments": [
                        {"type": "dialogue", "text": "你好", "character_ref": "A"},
                    ]
                },
                "characters_present": [],
                "location": {"name": "test"},
            }],
        }
        issues = critic._check_structure([ep])
        hook_issues = [i for i in issues if "hook" in i.category]
        assert len(hook_issues) >= 1

    def test_critic_detects_conflict_gap(self):
        """Critic should detect 4+ consecutive segments without action/emotion."""
        critic = DramaCriticAgent()
        ep = {
            "episode_index": 1,
            "scenes": [{
                "scene_id": "SC-E001-S001",
                "scene_index": 1,
                "content": {
                    "segments": [
                        {"type": "dialogue", "text": "A"},
                        {"type": "dialogue", "text": "B"},
                        {"type": "dialogue", "text": "C"},
                        {"type": "dialogue", "text": "D"},
                        {"type": "dialogue", "text": "E"},  # 5th = conflict gap
                    ]
                },
                "characters_present": [],
                "location": {"name": "test"},
            }],
        }
        issues = critic._check_conflict_density([ep])
        assert len(issues) >= 1

    @pytest.mark.asyncio
    async def test_critic_execute_heuristic_only(self):
        """Critic should produce feedback even without LLM."""
        critic = DramaCriticAgent(llm_service=None)
        script = make_sample_script()

        result = await critic.execute({"script": script, "project_input": make_project_input()})

        assert "overall_verdict" in result
        assert "total_score" in result
        assert "critical_issues" in result


# ── Tests: StyleGuard Agent ──


class TestStyleGuardAgent:
    """Test the StyleGuard agent's heuristic checks."""

    def test_style_guard_detects_tone_swings(self):
        """StyleGuard should flag extreme mood swings between adjacent scenes."""
        guard = StyleGuardAgent()
        ep = {
            "episode_index": 1,
            "scenes": [
                {"scene_index": 1, "location": {"mood": "comedy"}, "content": {"segments": []}, "characters_present": []},
                {"scene_index": 2, "location": {"mood": "tragedy"}, "content": {"segments": []}, "characters_present": []},
            ],
        }
        issues = guard._check_tone_consistency([ep])
        assert len(issues) >= 1

    def test_style_guard_detects_prohibited_content(self):
        """StyleGuard should flag content matching avoid_elements."""
        guard = StyleGuardAgent()
        ep = {
            "episode_index": 1,
            "scenes": [{
                "scene_id": "SC-E001-S001",
                "scene_index": 1,
                "content": {
                    "segments": [{"type": "dialogue", "text": "这里涉及色情内容", "character_ref": "A"}]
                },
                "characters_present": [],
                "location": {"name": "test"},
            }],
        }
        input_data = {"creative_direction": {"avoid_elements": ["色情"]}}
        issues = guard._check_content_safety([ep], input_data)
        assert len(issues) == 1
        assert issues[0].severity.value == "blocker"

    @pytest.mark.asyncio
    async def test_style_guard_execute_heuristic_only(self):
        """StyleGuard should produce feedback even without LLM."""
        guard = StyleGuardAgent(llm_service=None)
        script = make_sample_script()

        result = await guard.execute({
            "script": script,
            "style_preference": {"art_style": "anime"},
            "creative_direction": {"avoid_elements": []},
        })

        assert "overall_verdict" in result
        assert "total_score" in result


# ── Tests: Full Graph Integration ──


class TestStage1GraphIntegration:
    """Test the full Stage 1 LangGraph review loop with mock LLM."""

    @pytest.mark.asyncio
    async def test_graph_full_cycle_with_mock_llm(self):
        """Full generate → review → merge → approve cycle."""
        from app.agents.stage1_script.graph import create_stage1_graph

        mock_llm = MockLLMService()
        graph = create_stage1_graph(llm_service=mock_llm)

        initial_state = {
            "project_id": "PRJ-TEST001",
            "iteration": 1,
            "max_iterations": 3,
            "script": {},
            "input_data": make_project_input(),
            "drama_critic_feedback": None,
            "style_guard_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "review_history": [],
            "error": None,
        }

        result = await graph.ainvoke(initial_state)

        # Verify the graph completed
        assert result["merged_verdict"] in ("approved", "approved_with_minor", "escalated")
        assert "script" in result
        assert len(result.get("review_history", [])) >= 1
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_graph_without_llm_uses_heuristics(self):
        """Graph should complete with heuristic-only reviewers (no LLM)."""
        from app.agents.stage1_script.graph import create_stage1_graph

        graph = create_stage1_graph(llm_service=None)

        initial_state = {
            "project_id": "PRJ-TEST001",
            "iteration": 1,
            "max_iterations": 3,
            "script": make_sample_script(),  # Pre-existing script
            "input_data": make_project_input(),
            "drama_critic_feedback": None,
            "style_guard_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "review_history": [],
            "error": None,
        }

        result = await graph.ainvoke(initial_state)

        assert result["merged_verdict"] in ("approved", "approved_with_minor", "needs_revision")
        assert result.get("drama_critic_feedback") is not None
        assert result.get("style_guard_feedback") is not None


# ── Tests: PipelineRunner Stage 1 ──


class TestPipelineRunnerStage1:
    """Test PipelineRunner's Stage 1 integration."""

    @pytest.mark.asyncio
    async def test_runner_stage1_with_mock_llm(self):
        """PipelineRunner should execute Stage 1 and produce script output."""
        from app.agents.pipeline_runner import PipelineRunner

        mock_llm = MockLLMService()
        runner = PipelineRunner(project_id="PRJ-TEST001", llm_service=mock_llm)

        result = await runner._run_stage1(make_project_input(), emit=lambda e: None)

        assert "script_id" in result or "status" in result
        # Should have produced script content (from mock LLM)


# ── Run main for manual testing ──


async def main():
    """Manual integration test — prints results for visual inspection."""
    print("=" * 60)
    print("Stage 1 Integration Test — Manual Run")
    print("=" * 60)

    # 1. Schema validation
    print("\n[1] Testing Schema Validation...")
    script = StructuredScript.model_validate(make_sample_script())
    print(f"  [OK] Script validated: {script.summary()}")

    # 2. Writer with mock LLM
    print("\n[2] Testing Writer with Mock LLM...")
    mock_llm = MockLLMService()
    writer = ScriptWriterAgent(llm_service=mock_llm)
    result = await writer.execute(input_data=make_project_input())
    print(f"  [OK] Script generated: {result['script_id']}, {len(result['episodes'])} episodes")

    # 3. Critic review
    print("\n[3] Testing Critic Review...")
    critic = DramaCriticAgent(llm_service=mock_llm)
    review = await critic.execute(
        {"script": result, "project_input": make_project_input()},
        context={"llm_service": mock_llm},
    )
    print(f"  [OK] Critic score: {review['total_score']}, issues: {len(review['critical_issues'])}")

    # 4. StyleGuard review
    print("\n[4] Testing StyleGuard Review...")
    guard = StyleGuardAgent(llm_service=mock_llm)
    style_review = await guard.execute(
        {"script": result, "style_preference": {"art_style": "anime"}},
        context={"llm_service": mock_llm},
    )
    print(f"  [OK] Style score: {style_review['total_score']}, issues: {len(style_review['critical_issues'])}")

    # 5. Full graph
    print("\n[5] Testing Full Graph Cycle...")
    from app.agents.stage1_script.graph import create_stage1_graph

    graph = create_stage1_graph(llm_service=mock_llm)
    state_result = await graph.ainvoke({
        "project_id": "PRJ-TEST001",
        "iteration": 1,
        "max_iterations": 3,
        "script": {},
        "input_data": make_project_input(),
        "drama_critic_feedback": None,
        "style_guard_feedback": None,
        "merged_verdict": "pending",
        "merged_score": 0,
        "blocker_count": 0,
        "review_history": [],
        "error": None,
    })
    print(f"  [OK] Verdict: {state_result['merged_verdict']}, Score: {state_result['merged_score']}")
    print(f"  [OK] Review rounds: {len(state_result['review_history'])}")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
