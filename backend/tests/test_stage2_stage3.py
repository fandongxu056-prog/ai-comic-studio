"""Integration tests for Stage 2 (Asset Design) + Stage 3 (Storyboard) agents.

Run: pytest tests/test_stage2_stage3.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.stage2_asset import AssetProfiles, CharacterAsset, LocationAsset, StyleManifest
from app.schemas.stage3_storyboard import ShotPlan, Shot, EpisodeShot


# ── Mock LLM Service ──

class MockLLM:
    def __init__(self, return_data=None):
        self.data = return_data
        self.calls = []

    async def generate_structured(self, system_prompt, human_prompt, schema, **kw):
        self.calls.append({"system": system_prompt[:100], "human": human_prompt[:100], "schema": schema.__name__})
        if self.data:
            return schema.model_validate(self.data)
        # Parse how many items are in the input to return matching count
        import json
        input_items = 0
        try:
            data = json.loads(human_prompt)
            if isinstance(data, list):
                input_items = len(data)
        except Exception:
            pass
        if input_items < 1:
            input_items = 1
        if schema.__name__ == "CharList":
            from app.schemas.stage2_asset import CharacterAsset, Costume
            chars = []
            for i in range(input_items):
                c = CharacterAsset(ref_name=f"角色{i+1}", role_type="protagonist", character_prompt_template="test character, anime style")
                if not c.design_sheet.costumes:
                    c.design_sheet.costumes = [Costume(costume_id=f"COST-{i+1:04d}", name="默认", description="测试")]
                chars.append(c)
            return type("CharList", (), {"characters": chars})()
        if schema.__name__ == "LocList":
            locs = [LocationAsset(name=f"场景{i+1}", location_prompt_template="test location, anime background") for i in range(input_items)]
            return type("LocList", (), {"locations": locs})()
        return schema()


def make_script_for_assets():
    return {
        "script_id": "SCR-TEST",
        "character_index": [
            {"ref_name": "主角A", "role_type": "protagonist", "scene_count": 5, "traits_from_script": ["勇敢", "冲动"]},
            {"ref_name": "反派B", "role_type": "antagonist", "scene_count": 3, "traits_from_script": ["狡猾"]},
        ],
        "location_index": [
            {"name": "古城", "scene_count": 3},
            {"name": "密室", "scene_count": 2},
        ],
        "episodes": [
            {"episode_index": 1, "scenes": [
                {"location": {"name": "古城", "time_of_day": "night", "weather": "rain", "mood": "紧张"}, "characters_present": [{"character_ref": "主角A"}]},
                {"location": {"name": "密室", "time_of_day": "dawn", "weather": "fog", "mood": "神秘"}, "characters_present": [{"character_ref": "反派B"}]},
            ]},
        ],
    }


# ── Stage 2 Tests ──

class TestCharacterDesigner:
    @pytest.mark.asyncio
    async def test_heuristic_without_llm(self):
        from app.agents.stage2_asset.character_designer import CharacterDesignerAgent
        agent = CharacterDesignerAgent(llm_service=None)
        result = await agent.execute({"script": make_script_for_assets(), "style_preference": {"art_style": "anime"}})
        assert len(result["characters"]) == 2
        assert result["characters"][0]["ref_name"] == "主角A"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_with_mock_llm(self):
        from app.agents.stage2_asset.character_designer import CharacterDesignerAgent
        mock = MockLLM()
        agent = CharacterDesignerAgent(llm_service=mock)
        result = await agent.execute({"script": make_script_for_assets(), "style_preference": {}})
        assert len(result["characters"]) >= 1
        assert len(mock.calls) >= 1

    def test_empty_char_index(self):
        from app.agents.stage2_asset.character_designer import CharacterDesignerAgent
        import asyncio
        async def run():
            agent = CharacterDesignerAgent()
            result = await agent.execute({"script": {"character_index": []}})
            return result
        result = asyncio.run(run())
        assert result["characters"] == []


class TestSceneDesigner:
    @pytest.mark.asyncio
    async def test_heuristic_without_llm(self):
        from app.agents.stage2_asset.scene_designer import SceneDesignerAgent
        agent = SceneDesignerAgent(llm_service=None)
        result = await agent.execute({"script": make_script_for_assets(), "style_preference": {}})
        assert len(result["locations"]) == 2

    @pytest.mark.asyncio
    async def test_with_mock_llm(self):
        from app.agents.stage2_asset.scene_designer import SceneDesignerAgent
        mock = MockLLM()
        agent = SceneDesignerAgent(llm_service=mock)
        result = await agent.execute({"script": make_script_for_assets(), "style_preference": {}})
        assert len(result["locations"]) >= 1

    def test_scene_context_collection(self):
        from app.agents.stage2_asset.scene_designer import SceneDesignerAgent
        agent = SceneDesignerAgent()
        ctx = agent._collect_scene_context(make_script_for_assets()["episodes"])
        assert "古城" in ctx
        assert "night" in ctx["古城"]["times"]
        assert "rain" in ctx["古城"]["weathers"]


class TestPacingDirector:
    def test_shot_variety_check(self):
        from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
        agent = PacingDirectorAgent()
        # All same shot type → should flag
        episodes = [{"episode_index": 1, "scenes": [{"scene_id": "SC-1", "shots": [
            {"shot_id": "S1", "shot_type": "medium_shot", "duration_ms": 3000, "camera_movement": {"type": "static"}},
            {"shot_id": "S2", "shot_type": "medium_shot", "duration_ms": 3000, "camera_movement": {"type": "static"}},
            {"shot_id": "S3", "shot_type": "medium_shot", "duration_ms": 3000, "camera_movement": {"type": "static"}},
        ]}]}]
        issues = agent._check_shot_variety(episodes)
        assert len(issues) >= 1

    def test_duration_check(self):
        from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
        agent = PacingDirectorAgent()
        episodes = [{"episode_index": 1, "scenes": [{"scene_id": "SC-1", "shots": [
            {"shot_id": "S1", "shot_type": "long_shot", "duration_ms": 10000, "camera_movement": {"type": "static"}},
        ]}]}]
        issues = agent._check_duration_distribution(episodes)
        assert len(issues) >= 1  # static shot > 8s should flag

    def test_narrative_rhythm(self):
        from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
        agent = PacingDirectorAgent()
        episodes = [{"episode_index": 1, "scenes": [{"scene_id": "SC-1", "scene_mood": "紧张", "shots": [
            {"shot_id": "S1", "shot_type": "close_up", "duration_ms": 7000, "camera_movement": {"type": "static"}},
            {"shot_id": "S2", "shot_type": "close_up", "duration_ms": 7000, "camera_movement": {"type": "static"}},
        ]}]}]
        issues = agent._check_narrative_rhythm(episodes, {})
        assert len(issues) >= 1  # high tension + long avg → flag

    def test_composition_variety(self):
        from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
        agent = PacingDirectorAgent()
        episodes = [{"episode_index": 1, "scenes": [{"scene_id": "SC-1", "shots": [
            {"shot_id": "S1", "keyframe": {"composition": {"subject_focus": "center"}}, "duration_ms": 3000, "camera_movement": {"type": "static"}},
            {"shot_id": "S2", "keyframe": {"composition": {"subject_focus": "center"}}, "duration_ms": 3000, "camera_movement": {"type": "static"}},
            {"shot_id": "S3", "keyframe": {"composition": {"subject_focus": "center"}}, "duration_ms": 3000, "camera_movement": {"type": "static"}},
        ]}]}]
        issues = agent._check_composition_variety(episodes)
        assert len(issues) >= 1  # all centered → flag

    def test_visual_flow(self):
        from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
        agent = PacingDirectorAgent()
        episodes = [{"episode_index": 1, "scenes": [{"scene_id": "SC-1", "shots": [
            {"shot_id": f"S{i}", "shot_type": "medium_shot", "duration_ms": 3000, "camera_movement": {"type": "pan_left"}}
            for i in range(5)
        ]}]}]
        issues = agent._check_visual_flow(episodes)
        assert len(issues) >= 1  # many horizontal pans → flag 180 rule


# ── Stage 2/3 Schema Tests ──

class TestStage2Schema:
    def test_asset_profiles_validation(self):
        profile = AssetProfiles(
            project_id="PRJ-TEST",
            script_id="SCR-TEST",
            style_manifest=StyleManifest(art_style="anime", global_style_seed=42),
            characters=[CharacterAsset(ref_name="主角", role_type="protagonist")],
            locations=[LocationAsset(name="场景")],
        )
        assert profile.project_id == "PRJ-TEST"
        assert len(profile.characters) == 1

    def test_minimal_valid_profile(self):
        data = {
            "project_id": "X", "script_id": "Y",
            "style_manifest": {"art_style": "anime", "global_style_seed": 1},
            "characters": [{"ref_name": "A", "role_type": "protagonist"}],
            "locations": [{"name": "B"}],
        }
        profile = AssetProfiles.model_validate(data)
        assert profile.characters[0].ref_name == "A"

    def test_rejects_empty_characters(self):
        with pytest.raises(Exception):
            AssetProfiles.model_validate({"project_id": "X", "script_id": "Y", "style_manifest": {"art_style": "anime", "global_style_seed": 1}, "characters": [], "locations": [{"name": "B"}]})


class TestStage3Schema:
    def test_shot_plan_validation(self):
        plan = ShotPlan(
            project_id="PRJ-TEST",
            script_id="SCR-TEST",
            asset_set_id="AST-TEST",
            episodes=[EpisodeShot(episode_index=1, scenes=[{
                "scene_id": "SC-1",
                "shots": [Shot(shot_index=1, shot_type="medium_shot", duration_ms=3000, keyframe={"composition": {"subject_focus": "主角"}, "image_prompt": {"positive": "test prompt", "negative": "", "seed": 42}})]
            }])],
        )
        assert len(plan.episodes) == 1
        assert plan.episodes[0].scenes[0].shots[0].duration_ms == 3000


# ── Main ──

async def main():
    print("=" * 60)
    print("Stage 2/3 Integration Test")
    print("=" * 60)

    from app.agents.stage2_asset.character_designer import CharacterDesignerAgent
    from app.agents.stage2_asset.scene_designer import SceneDesignerAgent
    from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent

    mock = MockLL()
    script = make_script_for_assets()

    print("\n[1] CharacterDesigner with Mock LLM...")
    cd = CharacterDesignerAgent(llm_service=mock)
    result = await cd.execute({"script": script, "style_preference": {"art_style": "anime"}})
    print(f"  [OK] {len(result['characters'])} characters designed")

    print("\n[2] SceneDesigner with Mock LLM...")
    sd = SceneDesignerAgent(llm_service=mock)
    result = await sd.execute({"script": script, "style_preference": {}})
    print(f"  [OK] {len(result['locations'])} locations designed")

    print("\n[3] PacingDirector heuristic checks...")
    pd = PacingDirectorAgent()
    test_episodes = [{"episode_index": 1, "scenes": [{"scene_id": "S1", "shots": [
        {"shot_id": "SH1", "shot_type": "medium_shot", "duration_ms": 9000, "camera_movement": {"type": "static"}},
    ]}]}]
    issues = pd._check_duration_distribution(test_episodes)
    print(f"  [OK] {len(issues)} issues found")

    print("\n" + "=" * 60)
    print("All Stage 2/3 tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
