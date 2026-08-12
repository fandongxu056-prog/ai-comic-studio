/** Mock data for all 4 stages — used until backend is deployed. */

// ── Stage 1: Script ──

export const mockScript = {
  script_id: "SCR-A1B2C3D4",
  project_id: "PRJ-0001",
  version: 2,
  status: "review",
  episode_count: 3,
  scene_count: 9,
  character_count: 5,
  location_count: 4,
  latest_score: 82,
  latest_verdict: "approved_with_minor",
  episodes: [
    {
      episode_index: 1,
      title: "觉醒之夜",
      hook: "深夜加班回家的路上，林越看到了不该存在的东西",
      cliffhanger: "当她再次睁开眼，整个世界变得不一样了...",
      summary: "普通上班族林越在深夜偶遇灵气裂缝，意外觉醒异能",
      scenes: [
        {
          scene_id: "SC-E001-S001",
          scene_index: 1,
          location: { name: "深夜办公室", time_of_day: "night", mood: "疲惫" },
          characters_present: [
            { character_ref: "林越", emotional_state: "疲惫" },
            { character_ref: "王经理", emotional_state: "不耐烦" },
          ],
          content: {
            segments: [
              { type: "narration", text: "深夜十一点，霓虹灯在窗外闪烁", emotion_tag: "", action_tag: "" },
              { type: "action", text: "林越独自坐在工位上，揉了揉酸痛的眼睛", emotion_tag: "疲惫", action_tag: "揉眼" },
              { type: "dialogue", character_ref: "王经理", text: "林越，这个方案今晚必须完成。我先走了。", emotion_tag: "不耐烦", action_tag: "转身离开" },
              { type: "inner_monologue", character_ref: "林越", text: "又是这样...到底什么时候才能摆脱这种生活", emotion_tag: "压抑", action_tag: "" },
              { type: "action", text: "她关掉电脑，拿起包，走向电梯", emotion_tag: "", action_tag: "关电脑" },
            ],
          },
          props_mentioned: ["电脑", "文件", "咖啡杯"],
          visual_emphasis: ["深夜办公室的冷色调", "林越的疲惫表情"],
        },
        {
          scene_id: "SC-E001-S002",
          scene_index: 2,
          location: { name: "地下通道", time_of_day: "midnight", mood: "诡异" },
          characters_present: [
            { character_ref: "林越", emotional_state: "恐惧" },
            { character_ref: "黑袍人", emotional_state: "冷漠" },
          ],
          content: {
            segments: [
              { type: "narration", text: "地下通道的灯忽明忽暗，空气中有一种说不清的压迫感", emotion_tag: "", action_tag: "" },
              { type: "action", text: "林越停下脚步，回头望去——空无一人", emotion_tag: "警觉", action_tag: "回头" },
              { type: "dialogue", character_ref: "黑袍人", text: "别动。你身上有'灵气'的味道。", emotion_tag: "冷漠", action_tag: "从暗处走出" },
              { type: "dialogue", character_ref: "林越", text: "什...什么？你是谁？", emotion_tag: "恐惧", action_tag: "后退" },
              { type: "narration", text: "黑袍人的手指尖，一团青色的火焰无声燃起", emotion_tag: "", action_tag: "" },
              { type: "action", text: "林越的瞳孔骤然放大——这不是幻觉", emotion_tag: "震惊", action_tag: "瞳孔放大" },
            ],
          },
          props_mentioned: ["手机"],
          visual_emphasis: ["青色火焰", "黑袍人的身影", "林越震惊的表情"],
        },
        {
          scene_id: "SC-E001-S003",
          scene_index: 3,
          location: { name: "废弃工厂", time_of_day: "midnight", mood: "紧张" },
          characters_present: [
            { character_ref: "林越", emotional_state: "困惑" },
            { character_ref: "黑袍人", emotional_state: "解释中" },
          ],
          content: {
            segments: [
              { type: "narration", text: "废弃的工厂里，月光透过破损的屋顶洒在地面", emotion_tag: "", action_tag: "" },
              { type: "dialogue", character_ref: "黑袍人", text: "这个世界有两层——表层，和'灵气层'。你刚才看到的，是两层之间的裂缝。", emotion_tag: "解释" },
              { type: "dialogue", character_ref: "林越", text: "我...我从来没听说过", emotion_tag: "困惑", action_tag: "摇头" },
              { type: "dialogue", character_ref: "黑袍人", text: "因为你不该知道。但裂缝选中了你。从今天起，你不再是普通人。", emotion_tag: "郑重" },
              { type: "narration", text: "她感到体内有什么东西正在苏醒——一种从未有过的力量感", emotion_tag: "", action_tag: "" },
            ],
          },
          props_mentioned: [],
          visual_emphasis: ["月光光束", "灵气裂缝的光芒", "林越的转变"],
        },
      ],
    },
  ],
  character_index: [
    { ref_name: "林越", full_name: "林越", role_type: "protagonist", scene_count: 3, dialogue_count: 5 },
    { ref_name: "黑袍人", full_name: "未知", role_type: "supporting", scene_count: 2, dialogue_count: 4 },
    { ref_name: "王经理", full_name: "王建国", role_type: "cameo", scene_count: 1, dialogue_count: 1 },
  ],
  location_index: [
    { name: "深夜办公室", scene_count: 1 },
    { name: "地下通道", scene_count: 1 },
    { name: "废弃工厂", scene_count: 1 },
  ],
  review_history: [
    {
      round: 1,
      drama_critic_score: 75,
      style_guard_score: 80,
      merged_score: 78,
      verdict: "needs_revision",
      blocker_count: 1,
    },
    {
      round: 2,
      drama_critic_score: 84,
      style_guard_score: 80,
      merged_score: 82,
      verdict: "approved_with_minor",
      blocker_count: 0,
    },
  ],
};

// ── Stage 2: Assets ──

export const mockAssets = {
  asset_set_id: "AST-0001",
  characters: [
    {
      character_id: "CHAR-0001",
      ref_name: "林越",
      role_type: "protagonist",
      design_sheet: {
        appearance: {
          age_appearance: "24-26岁",
          gender: "女",
          body_type: "纤瘦，中等身高",
          face: { shape: "鹅蛋脸", eyes: "杏仁眼，深棕色", hair: "黑色长发，马尾" },
        },
        costumes: [
          { costume_id: "COST-0001", name: "通勤装", description: "白色衬衫+深灰西装裤，简约干练" },
        ],
        expressions: {
          neutral: "平静中带一丝疲惫",
          surprised: "瞳孔放大，嘴唇微张",
          determined: "眉头微皱，目光坚定",
        },
      },
      character_prompt_template: "24-year-old Chinese woman, slender, long black hair in ponytail, almond eyes, fair skin, anime art style",
    },
    {
      character_id: "CHAR-0002",
      ref_name: "黑袍人",
      role_type: "supporting",
      design_sheet: {
        appearance: {
          age_appearance: "30-35岁",
          gender: "男",
          body_type: "高大瘦削",
          face: { shape: "方脸", eyes: "锐利，灰色", hair: "银白色短发" },
        },
        costumes: [
          { costume_id: "COST-0002", name: "黑袍斗篷", description: "黑色长袍，兜帽遮住大半脸，袖口有暗纹" },
        ],
        expressions: {
          neutral: "冷漠",
          explaining: "目光深邃",
        },
      },
      character_prompt_template: "tall thin man, silver short hair, sharp grey eyes, black hooded cloak, mysterious aura, anime art style",
    },
  ],
  locations: [
    {
      location_id: "LOC-0001",
      name: "深夜办公室",
      design_sheet: { description: "现代化办公室，冷色调灯光，窗外霓虹夜景", key_features: ["开放式工位", "落地窗", "霓虹灯倒影"] },
      location_prompt_template: "modern office at night, cool fluorescent lighting, city lights through floor-to-ceiling windows, anime background art",
    },
    {
      location_id: "LOC-0002",
      name: "地下通道",
      design_sheet: { description: "昏暗的地下人行通道，头顶白炽灯闪烁，墙壁斑驳", key_features: ["闪烁灯光", "斑驳墙面", "狭长空间"] },
      location_prompt_template: "underground passageway, flickering ceiling lights, peeling walls, eerie atmosphere, anime background art",
    },
    {
      location_id: "LOC-0003",
      name: "废弃工厂",
      design_sheet: { description: "废弃工业厂房，月光从破洞屋顶射入，灰尘在光束中飘舞", key_features: ["月光光束", "锈蚀机械", "空旷厂房"] },
      location_prompt_template: "abandoned factory, moonlight beams through broken roof, dust particles in light, atmospheric anime background",
    },
  ],
  props: [
    { prop_id: "PROP-0001", name: "青色火焰", importance: "key_item", design: { description: "拳头大小的青色火焰，悬浮于掌心" } },
    { prop_id: "PROP-0002", name: "手机", importance: "recurring", design: { description: "普通智能手机" } },
  ],
  style_manifest: { art_style: "anime", global_style_seed: 42, color_palette: { name: "cool_dark", primary_colors: ["#1a1a2e", "#16213e", "#0f3460"] } },
  review_history: [{ round: 1, reviewer: "consistency_agent", verdict: "approved", total_score: 88 }],
};

// ── Stage 3: Storyboard ──

export const mockStoryboard = {
  storyboard_id: "STB-0001",
  total_shots: 9,
  total_duration_ms: 72000,
  episodes: [
    {
      episode_index: 1,
      title: "觉醒之夜",
      estimated_duration_ms: 72000,
      scenes: [
        {
          scene_id: "SC-E001-S001",
          location_id: "LOC-0001",
          scene_mood: "疲惫",
          shots: [
            {
              shot_id: "SH-E001-S001-001",
              shot_index: 1,
              shot_type: "long_shot",
              camera_angle: "eye_level",
              duration_ms: 8000,
              keyframe: {
                composition: { subject_focus: "林越在工位", foreground: "电脑屏幕", background: "空荡的办公室" },
                image_prompt: {
                  positive: "24-year-old Chinese woman in white shirt at office desk, long black hair ponytail, tired expression, modern office at night, cool fluorescent lighting, city lights through floor-to-ceiling windows, anime art style, clean linework, flat color illustration",
                  negative: "realistic, photorealistic, 3D, photograph",
                  seed: 421001001,
                },
              },
              dialogue: [],
            },
            {
              shot_id: "SH-E001-S001-002",
              shot_index: 2,
              shot_type: "medium_shot",
              camera_angle: "eye_level",
              duration_ms: 5000,
              keyframe: {
                composition: { subject_focus: "林越揉眼", foreground: "", background: "窗外夜景" },
                image_prompt: {
                  positive: "close-up of young Chinese woman rubbing tired eyes, dark circles, office background blurred, anime art style, emotional, detailed eyes",
                  negative: "realistic, photorealistic",
                  seed: 421001002,
                },
              },
              dialogue: [{ character_id: "CHAR-0001", text: "又是这样...", emotion: "压抑", start_ms: 1000, end_ms: 4000 }],
            },
            {
              shot_id: "SH-E001-S001-003",
              shot_index: 3,
              shot_type: "full_shot",
              camera_angle: "eye_level",
              duration_ms: 3000,
              keyframe: {
                composition: { subject_focus: "林越离开办公室", foreground: "", background: "走廊" },
                image_prompt: {
                  positive: "young woman walking away from desk, picking up bag, office corridor, anime art style, dynamic composition",
                  negative: "realistic, photorealistic",
                  seed: 421001003,
                },
              },
              dialogue: [],
            },
          ],
        },
        {
          scene_id: "SC-E001-S002",
          location_id: "LOC-0002",
          scene_mood: "诡异",
          shots: [
            {
              shot_id: "SH-E001-S002-001",
              shot_index: 1,
              shot_type: "long_shot",
              camera_angle: "low_angle",
              duration_ms: 6000,
              keyframe: {
                composition: { subject_focus: "林越走入地下通道", foreground: "入口楼梯", background: "昏暗通道" },
                image_prompt: {
                  positive: "young woman descending stairs into underground passage, flickering lights, eerie atmosphere, long shadows, anime art style, dramatic lighting",
                  negative: "realistic, 3D",
                  seed: 421002001,
                },
              },
              dialogue: [],
            },
            {
              shot_id: "SH-E001-S002-002",
              shot_index: 2,
              shot_type: "close_up",
              camera_angle: "eye_level",
              duration_ms: 5000,
              keyframe: {
                composition: { subject_focus: "林越惊恐的表情", foreground: "", background: "暗处人影" },
                image_prompt: {
                  positive: "extreme close-up of young woman's frightened face, eyes wide, dim lighting, shadowy figure reflected in her eyes, anime art style, intense emotion",
                  negative: "realistic, photorealistic",
                  seed: 421002002,
                },
              },
              dialogue: [{ character_id: "CHAR-0001", text: "...谁？", emotion: "恐惧", start_ms: 500, end_ms: 4000 }],
            },
            {
              shot_id: "SH-E001-S002-003",
              shot_index: 3,
              shot_type: "medium_shot",
              camera_angle: "dutch",
              duration_ms: 7000,
              keyframe: {
                composition: { subject_focus: "黑袍人手中青色火焰", foreground: "火焰光", background: "黑袍人轮廓" },
                image_prompt: {
                  positive: "mysterious figure in black hooded cloak, cyan flame floating above palm, illuminating face from below, underground passage, anime art style, dramatic chiaroscuro lighting",
                  negative: "realistic, 3D, photograph",
                  seed: 421002003,
                },
              },
              dialogue: [
                { character_id: "CHAR-0002", text: "别动。你身上有'灵气'的味道。", emotion: "冷漠", start_ms: 0, end_ms: 6000 },
              ],
            },
          ],
        },
      ],
    },
  ],
  tempo_analysis: {
    shot_duration_distribution: { ultra_short_count: 0, short_count: 3, medium_count: 5, long_count: 1 },
    pacing_curve: [
      { shot_index: 1, tension_level: 3 },
      { shot_index: 2, tension_level: 4 },
      { shot_index: 3, tension_level: 3 },
      { shot_index: 4, tension_level: 6 },
      { shot_index: 5, tension_level: 7 },
      { shot_index: 6, tension_level: 9 },
    ],
  },
  review_history: [{ round: 1, reviewer: "pacing_agent", verdict: "approved", total_score: 85 }],
};

// ── Stage 4: Production ──

export const mockProduction = {
  production_id: "PRD-0001",
  status: "partial_complete",
  shots_total: 9,
  shots_completed: 6,
  videos_exported: 0,
  total_cost_usd: 0.42,
  generated_assets: {
    by_shot_id: {
      "SH-E001-S001-001": { status: "complete", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 } },
      "SH-E001-S001-002": { status: "complete", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 }, video_segment: { duration_ms: 5000, cost_usd: 0.05 } },
      "SH-E001-S001-003": { status: "complete", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 } },
      "SH-E001-S002-001": { status: "complete", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 }, video_segment: { duration_ms: 6000, cost_usd: 0.06 } },
      "SH-E001-S002-002": { status: "image_done", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 } },
      "SH-E001-S002-003": { status: "video_generating", keyframe_image: { url: "", resolution: "1920x1080", cost_usd: 0.04 } },
      "SH-E001-S003-001": { status: "pending" },
      "SH-E001-S003-002": { status: "pending" },
      "SH-E001-S003-003": { status: "pending" },
    },
  },
  task_log: [
    { shot_id: "SH-E001-S001-001", type: "image_gen", status: "succeeded", duration_ms: 3200, cost_usd: 0.04 },
    { shot_id: "SH-E001-S001-002", type: "image_gen", status: "succeeded", duration_ms: 2800, cost_usd: 0.04 },
    { shot_id: "SH-E001-S001-002", type: "video_gen", status: "succeeded", duration_ms: 15000, cost_usd: 0.05 },
    { shot_id: "SH-E001-S002-001", type: "image_gen", status: "succeeded", duration_ms: 3100, cost_usd: 0.04 },
    { shot_id: "SH-E001-S002-001", type: "video_gen", status: "succeeded", duration_ms: 18000, cost_usd: 0.06 },
    { shot_id: "SH-E001-S002-002", type: "image_gen", status: "succeeded", duration_ms: 2900, cost_usd: 0.04 },
    { shot_id: "SH-E001-S002-003", type: "image_gen", status: "succeeded", duration_ms: 3500, cost_usd: 0.04 },
    { shot_id: "SH-E001-S002-003", type: "video_gen", status: "running", duration_ms: 0, cost_usd: 0 },
  ],
  cost_report: {
    total_cost_usd: 0.42,
    breakdown: { image_generation_cost_usd: 0.28, video_generation_cost_usd: 0.14, tts_generation_cost_usd: 0, compositing_cost_usd: 0 },
    budget_compliance: "under_budget",
  },
};
