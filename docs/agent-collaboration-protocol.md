# AI 漫剧创作平台 — Multi-Agent 协作协议与品控体系

> **核心哲学**
> - Agent 不是替代人类创作者，而是**多角度放大**人类创作者的判断力
> - 品控不是"挑错"，而是**从不同维度验证创作意图是否被完整传达**
> - 每一次 Agent 审查都必须给出**可操作的修改建议**，而非模糊评价

---

## 目录

1. [通用 Agent 协作协议](#1-通用-agent-协作协议)
2. [Stage 1: 剧本 Agent 协作与品控](#2-stage-1-剧本-agent-协作与品控)
3. [Stage 2: 资产设计 Agent 协作与品控](#3-stage-2-资产设计-agent-协作与品控)
4. [Stage 3: 分镜 Agent 协作与品控](#4-stage-3-分镜-agent-协作与品控)
5. [跨阶段连续性契约](#5-跨阶段连续性契约)
6. [Human-in-the-Loop 介入协议](#6-human-in-the-loop-介入协议)

---

## 1. 通用 Agent 协作协议

### 1.1 Agent 角色五元组

每个 Agent 由其五元组定义：

```jsonc
{
  "agent_id": "script_writer_v1",
  "role": {
    "identity": "资深漫剧编剧",
    "expertise": ["短剧叙事结构", "爽文节奏", "对白设计", "漫剧改编"],
    "personality": "敢于打破常规但尊重故事内核，擅长在有限篇幅内制造情绪爆点",
    "blind_spots": ["对画面可实现性不够敏感", "可能忽略预算约束"],
    "quality_bias": "更关注戏剧张力而非视觉美感"
  },
  "scope": {
    "stage": "script",
    "reads": ["project_input", "source_material"],
    "writes": ["structured_script"],
    "must_not_modify": ["character_design_sheets", "storyboard"]
  },
  "review_capability": {
    "can_review": [],
    "can_be_reviewed_by": ["drama_critic", "style_guard"]
  },
  "toolkit": ["script_structure_validator", "dialogue_density_analyzer", "conflict_curve_mapper"]
}
```

**设计原则**：
- 每个 Agent 明确声明自己的**能力盲区**——这是 Multi-Agent 协作的前提
- `can_be_reviewed_by` 定义了审查关系图，避免审查变成"所有人审所有人"的效率黑洞

### 1.2 通用消息格式

Agent 之间不进行自由对话，而是通过结构化消息交换：

```jsonc
{
  "message_id": "MSG-{uuid}",
  "timestamp": "2026-08-07T10:30:00Z",
  "sender": { "agent_id": "drama_critic_v1", "role": "reviewer" },
  "recipient": { "agent_id": "script_writer_v1", "role": "author" },

  "message_type": "review_feedback",  // review_feedback | revision_response | clarification | escalation

  "target_artifact": {
    "artifact_type": "episode_script",
    "artifact_ref": "episode_index=3",
    "version": 2
  },

  "content": {
    "overall_verdict": "needs_revision",  // approved | approved_with_minor | needs_revision | rejected
    "score": {
      "total": 72,  // 0-100
      "dimensions": {
        "story_completeness": 85,
        "conflict_density": 60,
        "dialogue_naturalness": 75,
        "pacing": 68,
        "filmability": 72
      }
    },
    "critical_issues": [
      {
        "id": "ISSUE-001",
        "severity": "blocker",  // blocker | major | minor | suggestion
        "location": "episode=3, scene=2, segment=5",
        "category": "conflict_density",
        "description": "连续4个对白segment没有冲突推进，观众会流失",
        "evidence": "Scene E003-S002 中 segment 3-6 共12句对白均为日常寒暄",
        "suggestion": "建议在 segment 4 插入一个突发事件或信息差揭露",
        "suggested_fix_example": "可在角色A说完'最近还好吗'后，角色B突然亮出一封信：'你妹妹的事，我都知道了'"
      }
    ],
    "strengths": [
      {
        "location": "episode=3, scene=1",
        "aspect": "开场悬念设置出色，3秒内建立信息差"
      }
    ],
    "continuity_flags": [
      {
        "rule_id": "CONT-RULE-005",
        "violation": "角色C在episode=1中设定为左撇子，本集segment=8中描述为右手持剑",
        "severity": "major"
      }
    ]
  },

  "reply_to": "MSG-{previous_message_id}",
  "iteration_round": 2,
  "ttl_rounds_remaining": 2
}
```

**关键设计**：
- `evidence` 必须引用到具体位置——杜绝模糊批评
- `suggested_fix_example` 给出可直接使用的修改范例——加速迭代
- `ttl_rounds_remaining` 防止无限循环审查

### 1.3 审查循环生命周期

```
┌────────────────────────────────────────────────────────────────┐
│                     CREATIVE ITERATION LOOP                     │
│                                                                │
│   Author Agent          Reviewer Agent(s)        Human         │
│   ────────────          ─────────────────        ─────         │
│       │                       │                    │           │
│       │  1. Submit Draft      │                    │           │
│       │─────────────────────→│                    │           │
│       │                       │                    │           │
│       │              2. Review (parallel)          │           │
│       │              ┌────────┴────────┐           │           │
│       │              │ Critic │ Style  │           │           │
│       │              └────────┬────────┘           │           │
│       │                       │                    │           │
│       │              3. Merge & Aggregate          │           │
│       │                       │                    │           │
│       │  4. Feedback           │                    │           │
│       │←─────────────────────│                    │           │
│       │                       │                    │           │
│   ┌───┴────────────┐          │                    │           │
│   │Can auto-fix?   │          │                    │           │
│   │(minor only)    │          │                    │           │
│   └───┬────────────┘          │                    │           │
│       │                       │                    │           │
│       │  NO (major/blocker)    │                    │           │
│       │──────────────────────────────────────────→│           │
│       │                       │    5. Escalate     │           │
│       │                       │    to Human        │           │
│       │                       │                    │           │
│       │              ┌────────┴────────┐           │           │
│       │              │  6. Human       │           │           │
│       │              │  Decision       │           │           │
│       │              └────────┬────────┘           │           │
│       │                       │                    │           │
│       │  7. Revised Draft     │                    │           │
│       │─────────────────────→│                    │           │
│       │                       │                    │           │
│       │        (loop continues until verdict=approved or TTL=0) │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 1.4 品控总框架：QC-5 五维质量模型

每个 Stage 的品控都从这五个维度评估，但各 Stage 的权重不同：

| 维度 | 定义 | Stage 1 权重 | Stage 2 权重 | Stage 3 权重 |
|------|------|:---------:|:---------:|:---------:|
| **完整性 (Completeness)** | 产出是否覆盖了所有必需的要素 | 25% | 20% | 15% |
| **一致性 (Consistency)** | 内部元素之间、与上游约定之间是否一致 | 15% | 40% | 30% |
| **品质感 (Quality)** | 创意/审美/叙事层面的高度 | 35% | 25% | 25% |
| **可执行性 (Executability)** | 下游阶段是否能直接使用 | 15% | 10% | 25% |
| **合规性 (Compliance)** | 是否遵守项目约束（时长/预算/风格） | 10% | 5% | 5% |

### 1.5 迭代收敛规则

```
硬性规则:
  1. 最多 3 轮审查迭代 (MAX_ROUNDS = 3)
  2. 每轮 blocker 数量必须递减，否则自动升级为人工介入
  3. 同一 issue 两轮未解决 → 自动升级为人工决策
  4. 第 3 轮仍存在 blocker → 强制人工介入，Agent 不再自行修改

软性规则:
  5. 总分≥80 且无 blocker → 自动通过
  6. 总分在 65-79 且无 blocker → 标记为 approved_with_minor，人工可快速过
  7. 总分<65 或有 blocker → 必须修订
```

---

## 2. Stage 1: 剧本 Agent 协作与品控

### 2.1 Agent 编队

```
                    ┌──────────────────┐
                    │   Orchestrator   │
                    │  (Script Lead)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  编剧 Agent │ │ 剧评 Agent │ │ 风格 Agent │
     │  (Author)  │ │  (Critic)  │ │(Style Guard)│
     └────────────┘ └────────────┘ └────────────┘
```

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **ScriptWriter** (Author) | 主创作：将源材料转化为结构化剧本 | ProjectInput + SourceMaterial | StructuredScript (draft) |
| **DramaCritic** (Reviewer) | 从叙事角度审查：节奏、冲突、人物弧光、对白 | ScriptWriter 的 draft | ReviewFeedback |
| **StyleGuard** (Reviewer) | 从风格/调性角度审查：题材一致性、台词风格、受众匹配 | ScriptWriter 的 draft + StylePreference | ReviewFeedback |

**为什么不是 2 个 Agent 而是 3 个？**

两个 Reviewer 覆盖了创意审查的**正交维度**——DramaCritic 管"好不好看"，StyleGuard 管"像不像这个品类"。两者不会互相干扰，也不会遗漏各自的盲区。

### 2.2 审查轮次协议

**Round 1: 结构和节奏审查**

DramaCritic + StyleGuard 并行审查 ScriptWriter 的一稿，侧重宏观问题：

```
DramaCritic Round 1 检查清单:
  □ 叙事结构完整性
    □ 第一集是否在 30 秒内建立核心悬念（hook）
    □ 每集结尾是否有有效 cliffhanger
    □ 整体是否遵循 "建立→发展→高潮→收束" 结构
  □ 冲突密度
    □ 每个场景是否至少有 1 个冲突点（信息差/利益冲突/情感对抗）
    □ 是否存在超过 3 个连续 segment 无冲突推进
  □ 人物弧光
    □ 主角是否在首集展示了核心欲望和困境
    □ 配角是否有独立于主角的存在价值
  □ 对白功能
    □ 每句对白是否至少满足一个功能：推进剧情/揭示性格/建立关系/埋下伏笔
    □ 是否有"废话对白"（单纯寒暄无信息量）

StyleGuard Round 1 检查清单:
  □ 题材对齐
    □ 核心冲突是否符合 genre.primary 的类型预期
    □ 是否有跨类型元素导致定位模糊
  □ 调性一致
    □ 喜剧场景是否在合适的位置（不宜在虐心段落出现）
    □ 情绪起伏是否在 target_emotion_curve 范围内
  □ 台词风格
    □ 角色台词是否与角色社会阶层/性格/时代背景匹配
    □ 是否有跳戏的现代词/网络梗（除非是都市题材）
  □ 受众匹配
    □ 内容尺度是否与 target_audience 匹配
    □ 是否有 avoid_elements 中指定的违禁内容
```

**Round 2: 细节和连续性审查**

如果 Round 1 通过，进入细节层面：

```
DramaCritic Round 2 检查清单:
  □ Scene 级别的节奏
    □ 每个场景的 segment 序列是否有情绪起伏
    □ 是否存在"平铺直叙"的场景（全程一个情绪调）
  □ 对白精准度
    □ 关键对话是否有"金句"潜质
    □ 角色情绪变化是否有铺垫（不突兀）
  □ 视觉潜力
    □ 每个场景是否提供了足够的视觉想象空间
    □ 是否有"纯对话场景"过于依赖语言而忽略画面

StyleGuard Round 2 检查清单:
  □ 角色声音差异化
    □ 不同角色的台词是否可以通过语气区分（不看名字也知道是谁在说话）
  □ 世界观细节
    □ 力量体系/设定的使用是否前后一致
    □ 是否有违反世界观规则的"bug"
```

**Round 3: 精简和打磨**

```
DramaCritic Round 3 检查清单:
  □ 是否可以删除某句对白而不影响理解
  □ 是否每个场景的 segment 数量在合理范围（8-15 个）
  □ 转场是否流畅

StyleGuard Round 3 检查清单:
  □ 全剧台词朗读流畅度
  □ 是否有重复的句式/词汇
  □ 关键情感节点的台词是否足够有力
```

### 2.3 品控评分细则 — Stage 1

```jsonc
{
  "qc_rubric": {
    "completeness": {
      "weight": 0.25,
      "criteria": [
        { "name": "episode_structure", "max_score": 30, "description": "每集是否有完整的 hook → 发展 → cliffhanger 结构" },
        { "name": "scene_coverage", "max_score": 25, "description": "每集场景数是否在合理范围（3-7个）且覆盖所有剧情需求" },
        { "name": "character_utilization", "max_score": 25, "description": "剧本角色索引是否包含了所有参与剧情的角色" },
        { "name": "segment_completeness", "max_score": 20, "description": "每个 segment 的类型/角色/文本/情绪标签是否完整填写" }
      ]
    },
    "consistency": {
      "weight": 0.15,
      "criteria": [
        { "name": "character_continuity", "max_score": 40, "description": "角色性格、能力、关系在跨场景/跨集中是否一致" },
        { "name": "world_rules_compliance", "max_score": 30, "description": "世界观的设定是否被严格遵守" },
        { "name": "timeline_coherence", "max_score": 30, "description": "时间线事件的前后因果关系是否成立" }
      ]
    },
    "quality": {
      "weight": 0.35,
      "criteria": [
        { "name": "hook_strength", "max_score": 20, "description": "开场 hook 的吸引力和信息差设置" },
        { "name": "conflict_density", "max_score": 25, "description": "冲突点的频率和强度分布" },
        { "name": "dialogue_naturalness", "max_score": 20, "description": "对白的口语化程度和角色区分度" },
        { "name": "emotional_curve", "max_score": 20, "description": "情绪起伏是否有效且不突兀" },
        { "name": "golden_lines", "max_score": 15, "description": "是否有令人印象深刻的'金句'" }
      ]
    },
    "executability": {
      "weight": 0.15,
      "criteria": [
        { "name": "visual_clarity", "max_score": 40, "description": "每个场景是否清晰地描述了可见的画面内容" },
        { "name": "location_descriptiveness", "max_score": 30, "description": "地点描述是否为后续场景设计提供了足够信息" },
        { "name": "prop_necessity", "max_score": 30, "description": "道具提及是否明确且必要（无关道具会浪费 Stage 2/3/4 成本）" }
      ]
    },
    "compliance": {
      "weight": 0.10,
      "criteria": [
        { "name": "duration_target", "max_score": 40, "description": "预估总时长是否在 target_duration 的 ±20% 范围内" },
        { "name": "genre_alignment", "max_score": 30, "description": "是否与指定的题材/风格保持一致" },
        { "name": "content_safety", "max_score": 30, "description": "是否包含 avoid_elements 中指定的违禁内容" }
      ]
    }
  }
}
```

**评分规则**：

- 每项 criteria 由 Reviewer Agent 按 0-`max_score` 打分
- `completeness_score = Σ(criteria_i.score) / Σ(criteria_i.max_score) × 100`
- `total_score = Σ(dimension_score × dimension_weight)`
- **合格线**：total ≥ 80，无 blocker
- **需修改**：total < 65 或存在 blocker
- **人工确认**：65 ≤ total < 80 且无 blocker → `approved_with_minor`

---

## 3. Stage 2: 资产设计 Agent 协作与品控

### 3.1 Agent 编队

```
                    ┌──────────────────┐
                    │   Orchestrator   │
                    │ (Asset Director) │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 角色设计 Agent   │ │ 场景设计 Agent   │ │ 道具设计 Agent   │
│ (CharDesigner)  │ │ (SceneDesigner) │ │ (PropDesigner)  │
│    (Author)     │ │    (Author)     │ │    (Author)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ 一致性审查 Agent      │
                  │ (ConsistencyAuditor) │
                  │     (Reviewer)       │
                  └─────────────────────┘
```

Stage 2 的 Agent 编队是**3 个并行 Author + 1 个集中 Reviewer**。三个设计 Agent 各司其职，不互相审查（角色设计 Agent 不具备评判场景设计的权威性），而是由一个专门的 ConsistencyAuditor 做跨资产一致性审查。

### 3.2 审查轮次协议

**Round 1: 独立设计 + 交叉一致性审查**

三个 Author Agent 并行产出各自的设计稿，然后 ConsistencyAuditor 集中审查：

```
ConsistencyAuditor Round 1 检查清单:
  □ 风格统一性
    □ 所有角色的 art_style 是否与 style_manifest 一致
    □ 角色A和角色B放在同一画面中，风格是否协调
    □ 场景的风格细节是否与角色风格匹配（线条粗细、上色方式等）
  □ 尺寸/比例一致性
    □ 角色身高比例是否合理（角色之间的相对身高）
    □ 道具尺寸是否与角色/场景匹配（杯子不能比头大）
  □ 色彩协调性
    □ 所有资产使用的色板是否在 style_manifest.color_palette 范围内
    □ 是否有角色色彩与常驻场景背景色过于接近（会糊在一起）
  □ 资产覆盖完整性
    □ 剧本中出现的所有角色是否都有设计稿
    □ 剧本中出现的所有场景是否都有设计稿
    □ 剧本道具索引中的 key_item 类道具是否都有设计稿
  □ 可辨识度
    □ 任何两个角色在外貌上是否有足够的区分度
    □ 同性别/同年龄段角色是否存在"撞脸"问题
```

**Round 2: 资产细化 + 功能性审查**

```
ConsistencyAuditor Round 2 检查清单:
  □ 服装逻辑
    □ 同一角色在多套服装之间，核心面部特征是否不变
    □ 每套服装的 scenes_used_in 是否合理（角色不会在连续场景中无故换装）
  □ 表情一致性
    □ 同一角色的不同表情，面部结构是否保持不变
    □ 表情描述是否可被生图模型稳定还原
  □ 场景功能性
    □ 每个场景的 layout_notes 是否为分镜阶段提供了构图参考
    □ 场景 variations 是否覆盖了剧本中出现的所有时间/天气条件
  □ 提示词质量
    □ 每个资产的 prompt_template 是否可直接与其他资产拼接而不产生风格漂移
    □ 提示词中是否包含了 style_manifest.global_negative_prompt 的约束
```

### 3.3 品控评分细则 — Stage 2

```jsonc
{
  "qc_rubric": {
    "completeness": {
      "weight": 0.20,
      "criteria": [
        { "name": "character_coverage", "max_score": 30, "description": "剧本角色索引中的所有角色是否都有设计稿" },
        { "name": "location_coverage", "max_score": 25, "description": "剧本中所有场景是否都有设计稿" },
        { "name": "prop_coverage", "max_score": 15, "description": "key_item 和 recurring 道具是否都有设计稿" },
        { "name": "costume_coverage", "max_score": 15, "description": "每个角色的每套标注服装是否都完成设计" },
        { "name": "expression_coverage", "max_score": 15, "description": "每个角色是否定义了至少 5 种关键表情" }
      ]
    },
    "consistency": {
      "weight": 0.40,
      "criteria": [
        { "name": "style_uniformity", "max_score": 25, "description": "所有资产是否共享同一个 style_manifest 的视觉语言" },
        { "name": "character_differentiation", "max_score": 25, "description": "任何两个角色在视觉上是否可清晰区分" },
        { "name": "scale_proportion", "max_score": 20, "description": "角色/场景/道具之间的相对比例是否合理" },
        { "name": "color_harmony", "max_score": 15, "description": "资产色彩是否在 color_palette 范围内且不冲突" },
        { "name": "costume_face_consistency", "max_score": 15, "description": "同一角色在不同服装下是否保持面部识别特征不变" }
      ]
    },
    "quality": {
      "weight": 0.25,
      "criteria": [
        { "name": "design_memorability", "max_score": 25, "description": "角色设计是否有令人印象深刻的辨识特征" },
        { "name": "design_functionality", "max_score": 25, "description": "外观设计是否服务于角色性格/身份/剧情" },
        { "name": "scene_atmosphere", "max_score": 25, "description": "场景设计是否有效传达了空间氛围和情绪基调" },
        { "name": "prop_detail_level", "max_score": 25, "description": "道具设计描述的精细度是否满足生图需求" }
      ]
    },
    "executability": {
      "weight": 0.10,
      "criteria": [
        { "name": "prompt_template_quality", "max_score": 40, "description": "prompt_template 是否可以稳定复现该资产的视觉特征" },
        { "name": "reference_image_readiness", "max_score": 30, "description": "参考图描述是否足够详细以生成有效的角色参考图" },
        { "name": "cross_asset_prompt_compatibility", "max_score": 30, "description": "不同资产的 prompt 拼接后是否仍能保持风格统一" }
      ]
    },
    "compliance": {
      "weight": 0.05,
      "criteria": [
        { "name": "style_constraint_adherence", "max_score": 50, "description": "是否严格遵守了 style_manifest 中的所有约束" },
        { "name": "art_style_alignment", "max_score": 50, "description": "art_style 选择是否与 project_input 一致" }
      ]
    }
  }
}
```

**Stage 2 的特殊性**：一致性权重 40%——这是整个项目视觉连贯性的根基。如果 Stage 2 的一致性出问题，Stage 3/4 的生图会直接翻车。

---

## 4. Stage 3: 分镜 Agent 协作与品控

### 4.1 Agent 编队

```
                    ┌──────────────────┐
                    │   Orchestrator   │
                    │  (Shot Director) │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 分镜构建 Agent   │ │ 节奏导演 Agent   │ │ 连续性检查 Agent  │
│ (ShotComposer)  │ │ (PacingDirector)│ │(ContinuityCheck)│
│    (Author)     │ │   (Reviewer)    │ │   (Reviewer)    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    (并行审查，不互审)
```

两个 Reviewer 同时审查 ShotComposer 的产出，但审查维度完全不同：

| Reviewer | 审查维度 | 如果出问题会导致... |
|----------|---------|-------------------|
| **PacingDirector** | 时长分配、镜头节奏、情绪起伏 | 成片拖沓或跳跃，观众失去耐心 |
| **ContinuityCheck** | 角色/场景/道具引用正确性、连续性规则遵守 | 画面出现"穿帮"，破坏沉浸感 |

### 4.2 审查轮次协议

**Round 1: 镜头语言和节奏审查（PacingDirector 主导）**

```
PacingDirector Round 1 检查清单:
  □ 景别多样性
    □ 一场戏内是否有景别变化（不能全是中景对打）
    □ 景别选择是否服务于叙事（特写用在了情感点、远景用在了建立场景）
  □ 镜头时长分布
    □ 是否有连续5个以上镜头时长相似（说明节奏平）
    □ 动作场景的镜头是否比对话场景短（应该短）
    □ 情绪爆点是否给了足够的镜头时长（不应该一闪而过）
    □ 时长分布是否符合 shot_duration_distribution 的合理比例
  □ 运镜合理性
    □ 运镜类型是否与场景情绪匹配（悲伤场景不宜快速推拉）
    □ 同一场景内的运镜是否有变化
    □ 是否有过多 static 镜头导致画面呆板
  □ 叙事节奏
    □ 高张力场景的镜头切换频率是否明显高于铺垫场景
    □ cliffhanger 镜头的时长和构图是否有效制造悬念

ContinuityCheck Round 1 检查清单:
  □ 角色引用正确性
    □ 每个 shot 的 characters_in_frame.character_id 是否存在于 AssetProfiles
    □ 每个 shot 引用的 costume_id 是否属于该角色
  □ 场景引用正确性
    □ 每个 shot 的 scene_id 对应的 location_id 是否存在于 AssetProfiles
    □ 场景 variation 是否与剧本中的 time_of_day/weather 一致
  □ 道具引用正确性
    □ props_in_frame 中的 prop_id 是否存在于 AssetProfiles
    □ 道具是否在它应该出现的场景中
  □ 对话-角色匹配
    □ dialogue 中的 character_id 是否与 characters_in_frame 一致或合理（画外音可不同）
```

**Round 2: 构图和提示词质量审查**

```
PacingDirector Round 2 检查清单:
  □ 构图多样性
    □ 同一场景内的构图是否有变化（rule_of_thirds 位置、depth_of_field）
    □ 是否存在"对话正反打"以外的构图方式
  □ 视觉流
    □ 连续镜头的视线方向和运动方向是否连贯（不要上一镜头向左、下一镜头也向左但角色已转身）

ContinuityCheck Round 2 检查清单:
  □ 提示词连续性
    □ image_prompt 是否正确注入了角色的 character_prompt_template
    □ image_prompt 是否正确注入了场景的 location_prompt_template
    □ 连续镜头的 seed 是否合理偏移（避免完全不同的风格）
  □ 角色连续状态
    □ 同一场景内，角色的 costume_id、emotional_state 是否连贯
    □ 角色的姿态和位置在连续镜头间是否合理
    □ 如果有受伤/换装/状态改变，是否在相邻镜头间正确体现
  □ 转场合理性
    □ transition 类型是否与场景切换的情绪需求匹配
    □ 是否存在不合理的 jump cut（同场景同角色同角度跳切）
```

**Round 3: 可执行性和最终检查**

```
PacingDirector + ContinuityCheck 合并检查:
  □ 提示词可执行性
    □ image_prompt.positive 是否在 4000 字符以内
    □ 提示词中的角色/场景引用拼接是否正确（无残留占位符）
    □ model_params 是否在所选模型的合理范围内
  □ 时长合理性
    □ 每个 shot 的 duration_ms 是否足够观众阅读对白（按每秒3字算）
    □ episode_total_duration_ms 是否在 target 的 ±15% 范围内
    □ dialogue 的 start_ms/end_ms 是否在 shot 的 duration_ms 范围内
  □ 最终一致性
    □ 全量 shot 的 shot_id 是否唯一且连续
    □ scene_shot_count 和 episode_shot_count 是否与实际数量一致
```

### 4.3 品控评分细则 — Stage 3

```jsonc
{
  "qc_rubric": {
    "completeness": {
      "weight": 0.15,
      "criteria": [
        { "name": "shot_coverage", "max_score": 30, "description": "剧本的每个 scene 是否都被拆解为镜头" },
        { "name": "dialogue_coverage", "max_score": 25, "description": "剧本的每句对白是否都映射到了某个 shot" },
        { "name": "field_completeness", "max_score": 25, "description": "每个 shot 的所有必填字段是否完整" },
        { "name": "asset_reference_completeness", "max_score": 20, "description": "每个 shot 是否引用了必要的角色/场景/道具" }
      ]
    },
    "consistency": {
      "weight": 0.30,
      "criteria": [
        { "name": "character_consistency", "max_score": 25, "description": "角色引用/服装/状态在连续镜头间是否连贯" },
        { "name": "scene_consistency", "max_score": 20, "description": "场景引用和时间/天气 variation 是否正确" },
        { "name": "prompt_continuity", "max_score": 25, "description": "提示词是否一致地引用了角色和场景模板" },
        { "name": "transition_logic", "max_score": 15, "description": "转场选择是否合理" },
        { "name": "spatial_continuity", "max_score": 15, "description": "角色的空间位置和运动方向是否连贯" }
      ]
    },
    "quality": {
      "weight": 0.25,
      "criteria": [
        { "name": "shot_variety", "max_score": 20, "description": "景别/角度/运镜是否有足够的多样性" },
        { "name": "composition_strength", "max_score": 25, "description": "每个镜头的构图是否有明确的视觉焦点和美感" },
        { "name": "narrative_clarity", "max_score": 25, "description": "每个镜头是否传达了清晰的叙事信息" },
        { "name": "emotional_resonance", "max_score": 15, "description": "镜头选择是否增强了情绪表达" },
        { "name": "pacing_quality", "max_score": 15, "description": "镜头时长分配是否创造了有效的叙事节奏" }
      ]
    },
    "executability": {
      "weight": 0.25,
      "criteria": [
        { "name": "prompt_executability", "max_score": 30, "description": "image_prompt 是否可直接用于生图API调用" },
        { "name": "video_prompt_readiness", "max_score": 20, "description": "video_prompt 是否完整可执行" },
        { "name": "dialogue_timing_accuracy", "max_score": 20, "description": "对白时间码是否在镜头时长范围内且合理" },
        { "name": "duration_reasonableness", "max_score": 15, "description": "每个镜头的时长是否足够观众消化画面和对白" },
        { "name": "audio_clarity", "max_score": 15, "description": "audio_notes 是否为 Stage 4 提供了明确的音效/配乐指引" }
      ]
    },
    "compliance": {
      "weight": 0.05,
      "criteria": [
        { "name": "duration_compliance", "max_score": 50, "description": "总时长是否在 target 范围" },
        { "name": "continuity_rules_compliance", "max_score": 50, "description": "是否遵守了所有 continuity_rules" }
      ]
    }
  }
}
```

**Stage 3 的特殊性**：可执行性权重 25%——如果说 Stage 1-2 允许一定的"创意模糊"，Stage 3 的输出必须**精确到像素和毫秒**，因为 Stage 4 是无判断力的 Pipeline。

---

## 5. 跨阶段连续性契约

### 5.1 设计动机

单一 Stage 内的 Agent 审查只能保证该 Stage 内部的质量，但跨 Stage 的"翻译损耗"是更隐蔽的质量杀手。连续性契约（Continuity Contract）是一套**自动校验规则**，不需要 Agent 参与，在 Stage 产出时自动运行。

### 5.2 契约层级

```
                    ┌─────────────────────┐
                    │  Stage 1 Contract   │
                    │  剧本层面约定        │
                    │  "角色A在第3集之前  │
                    │   不能使用那把剑"    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Stage 2 Contract   │
                    │  资产层面约定        │
                    │  "角色A的剑需要在   │
                    │   道具库中注册为     │
                    │   PROP-0003"        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Stage 3 Contract   │
                    │  分镜层面约定        │
                    │  "镜头 SH-E003-*    │
                    │   中角色A持剑时，   │
                    │   必须引用 PROP-0003"│
                    └─────────────────────┘
```

### 5.3 Stage 1 → Stage 2 契约

```jsonc
{
  "contract_s1_to_s2": {
    "rules": [
      {
        "id": "CROSS-S1-001",
        "type": "entity_coverage",
        "description": "Stage 1 character_index 中的所有角色必须在 Stage 2 characters 中有对应设计稿",
        "validation": "Stage1.character_index.characters[].ref_name ⊆ Stage2.characters[].ref_name",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S1-002",
        "type": "entity_coverage",
        "description": "Stage 1 location_index 中的所有地点必须在 Stage 2 locations 中有对应设计稿",
        "validation": "Stage1.location_index.locations[].name ⊆ Stage2.locations[].name",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S1-003",
        "type": "entity_coverage",
        "description": "Stage 1 prop_index 中 importance=key_item 或 recurring 的道具必须在 Stage 2 props 中有对应设计稿",
        "validation": "Stage1.prop_index.props[importance in (key_item, recurring)][].name ⊆ Stage2.props[].name",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S1-004",
        "type": "style_alignment",
        "description": "Stage 2 style_manifest.art_style 必须与 ProjectInput.style_preference.art_style 一致",
        "validation": "Stage2.style_manifest.art_style == ProjectInput.style_preference.art_style",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S1-005",
        "type": "costume_logic",
        "description": "每个角色的 costumes 必须覆盖该角色在剧本中出现的所有场景",
        "validation": "对于每个 character，其 costumes[].scenes_used_in 的并集必须包含该角色出现的所有 scene_id",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S1-006",
        "type": "scene_variation_coverage",
        "description": "每个场景的 variations 必须覆盖剧本中该场景出现的所有 time_of_day 和 weather 组合",
        "validation": "Stage1.scenes[location=loc].unique(time_of_day, weather) ⊆ Stage2.locations[name=loc].variations",
        "on_violation": "minor"
      }
    ]
  }
}
```

### 5.4 Stage 2 → Stage 3 契约

```jsonc
{
  "contract_s2_to_s3": {
    "rules": [
      {
        "id": "CROSS-S2-001",
        "type": "character_reference",
        "description": "每个 shot 的 characters_in_frame[].character_id 必须存在于 Stage 2 characters",
        "validation": "∀ shot: shot.characters_in_frame[].character_id ⊆ Stage2.characters[].character_id",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S2-002",
        "type": "costume_reference",
        "description": "每个 shot 中角色的 costume_id 必须属于该角色在 Stage 2 中定义的服装",
        "validation": "shot.characters_in_frame[].costume_id ∈ Stage2.characters[character_id].costumes[].costume_id",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S2-003",
        "type": "location_reference",
        "description": "每个 shot 的 scene 所引用的 location_id 必须存在于 Stage 2 locations",
        "validation": "∀ shot: shot的location_id ∈ Stage2.locations[].location_id",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S2-004",
        "type": "prop_reference",
        "description": "每个 shot 的 props_in_frame[].prop_id 必须存在于 Stage 2 props",
        "validation": "∀ shot: shot.props_in_frame[].prop_id ⊆ Stage2.props[].prop_id",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S2-005",
        "type": "prompt_injection",
        "description": "每个 shot 的 image_prompt.positive 必须包含对应 character 的 character_prompt_template 和对应 location 的 location_prompt_template",
        "validation": "检查 prompt 字符串中是否包含了角色和场景的核心特征词",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S2-006",
        "type": "style_seed_continuity",
        "description": "同一 episode 内所有 shot 的 image_prompt.seed 必须基于 style_manifest.global_style_seed 进行确定性偏移",
        "validation": "shot.image_prompt.seed == global_seed + shot_index * prime_offset",
        "on_violation": "major"
      }
    ]
  }
}
```

### 5.5 Stage 3 → Stage 4 契约

```jsonc
{
  "contract_s3_to_s4": {
    "rules": [
      {
        "id": "CROSS-S3-001",
        "type": "prompt_completeness",
        "description": "每个 shot 必须有完整的 image_prompt（positive + negative + seed + model_params）",
        "validation": "∀ shot: shot.keyframe.image_prompt 所有 required 字段不为空",
        "on_violation": "blocker"
      },
      {
        "id": "CROSS-S3-002",
        "type": "dialogue_timing",
        "description": "每个 shot 的 dialogue[].end_ms ≤ shot.duration_ms",
        "validation": "∀ shot, ∀ dialogue: dialogue.end_ms <= shot.duration_ms",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S3-003",
        "type": "episode_duration",
        "description": "每集的总 duration_ms 必须在 target 的 ±15% 范围内",
        "validation": "|episode_total_duration_ms - target_duration_ms| / target_duration_ms ≤ 0.15",
        "on_violation": "major"
      },
      {
        "id": "CROSS-S3-004",
        "type": "asset_urls",
        "description": "Stage 3 引用的所有 asset reference image URLs 必须有效（非 404）",
        "validation": "HTTP HEAD 检查所有 reference_images URL",
        "on_violation": "blocker"
      }
    ]
  }
}
```

### 5.6 契约执行机制

契约不是建议——是**硬约束**：

```
每条契约规则有一个 on_violation 级别:
  - blocker → 禁止进入下一 Stage，必须回退修改
  - major   → 允许进入但标记为 "有风险"，Human 必须确认
  - minor   → 自动记录 warning，不阻塞流程

契约校验时机:
  - Stage N 点击 "提交审批" 时自动运行
  - Stage N+1 开始前（Orchestrator 检查上游是否满足契约）
  - 上游 Stage 发生 revision 时，重新校验所有下游契约
```

---

## 6. Human-in-the-Loop 介入协议

### 6.1 介入点设计

不是每个环节都需要人介入。以下是**最小必要介入点**：

```
Stage 1: 剧本
  ┌──────────────────────────────────────────────────────────┐
  │  Agent 迭代 1-2 轮                                       │
  │      ↓                                                   │
  │  🛑 CHECKPOINT 1: 剧本大纲确认                            │
  │     用户确认：故事方向、核心冲突、集数分配                  │
  │      ↓                                                   │
  │  Agent 迭代细化场景和对白 (第3轮可能触发人工)               │
  │      ↓                                                   │
  │  🛑 CHECKPOINT 2: 全剧本审批                              │
  │     用户逐集确认或批量通过                                 │
  └──────────────────────────────────────────────────────────┘

Stage 2: 资产
  ┌──────────────────────────────────────────────────────────┐
  │  三个设计 Agent 并行产出                                  │
  │      ↓                                                   │
  │  🛑 CHECKPOINT 3: 角色设计确认                            │
  │     用户确认每个角色的外貌、服装、表情（可单独修改）         │
  │     场景和道具由 Agent 自动通过（除非 ConsistencyAuditor 报警）│
  └──────────────────────────────────────────────────────────┘

Stage 3: 分镜
  ┌──────────────────────────────────────────────────────────┐
  │  ShotComposer + 两个 Reviewer 迭代                        │
  │      ↓                                                   │
  │  🛑 CHECKPOINT 4: 关键场景分镜确认                        │
  │     只展示高潮/转折/结尾场景的分镜，其余自动通过            │
  │     用户可展开查看任意场景但非必须                         │
  └──────────────────────────────────────────────────────────┘

Stage 4: 制作
  ┌──────────────────────────────────────────────────────────┐
  │  Pipeline 自动执行（不阻塞）                               │
  │      ↓                                                   │
  │  🛑 CHECKPOINT 5: 成片预览                                │
  │     每集成片后展示，用户可标记问题镜头要求重新生成           │
  └──────────────────────────────────────────────────────────┘
```

### 6.2 智能筛选：哪些内容需要人工确认

```jsonc
{
  "human_review_filter": {
    "stage1_script": {
      "auto_pass_conditions": [
        "total_score ≥ 85 AND all dimension scores ≥ 70 AND zero blocker",
        "delta_from_previous_version ≤ 5% (仅微调)"
      ],
      "force_review_conditions": [
        "blocker_count > 0",
        "总时长偏离 target 超过 20%",
        "新增或删除了角色",
        "修改了核心冲突设定",
        "首次提交（无历史版本）"
      ],
      "review_depth": "episode_summary_only",  // 默认只展示每集概要不展示完整剧本
      "expand_on_user_request": true
    },
    "stage2_assets": {
      "auto_pass_conditions": [
        "所有角色 design_sheet 的 completeness ≥ 90",
        "ConsistencyAuditor 评分 ≥ 85",
        "仅修改了 prop 设计"
      ],
      "force_review_conditions": [
        "主角/反派角色首次创建或大幅度修改",
        "全局 style_manifest 变更",
        "ConsistencyAuditor 发现 major 级别一致性违规"
      ],
      "review_depth": "characters_only",  // 默认只展示角色设计，场景/道具自动通过
      "expand_on_user_request": true
    },
    "stage3_storyboard": {
      "auto_pass_conditions": [
        "PacingDirector 评分 ≥ 80 AND ContinuityCheck 评分 ≥ 85",
        "仅修改了非关键场景的分镜"
      ],
      "force_review_conditions": [
        "关键场景（hook/cliffhanger/climax）含 blocker",
        "总时长偏离 target 超过 15%",
        "ContinuityCheck 发现角色/场景引用错误"
      ],
      "review_depth": "key_scenes_only",  // 默认只展示 hook/cliffhanger/climax 的分镜
      "key_scene_types": ["hook", "cliffhanger", "climax", "emotional_peak"],
      "expand_on_user_request": true
    }
  }
}
```

### 6.3 人工介入的 UI 信息密度

当需要人工确认时，展示的信息遵循**逐层下钻**原则：

```
Layer 1 (摘要视图):
  ┌─────────────────────────────────────────┐
  │  Stage 1 剧本 - Round 2 审查完成         │
  │  ⭐ 总分: 82/100  ✅ 无 blocker           │
  │  📊 完整: 88 | 一致: 75 | 品质: 80       │
  │     可执行: 85 | 合规: 90                │
  │  📝 2 个 major issue, 5 个 minor         │
  │  ⏱️ 预估时长: 2分15秒 (目标 2分)          │
  │                                          │
  │  [查看详情] [逐集预览] [一键通过]         │
  └─────────────────────────────────────────┘

Layer 2 (点击"查看详情"后):
  ┌─────────────────────────────────────────┐
  │  🔴 Major Issues:                        │
  │  ├─ E03-S02: 冲突密度不足 (DramaCritic)  │
  │  │   连续4段对白无冲突，建议插入突发信息    │
  │  │   [查看建议修改] [忽略]                │
  │  │                                       │
  │  └─ E05-S01: 角色B台词风格不匹配          │
  │      (StyleGuard)                         │
  │      [查看建议修改] [忽略]                │
  │                                           │
  │  🟡 Minor Issues (5): [展开]              │
  │  🟢 Strengths (3): [展开]                 │
  └─────────────────────────────────────────┘

Layer 3 (点击具体 issue 后):
  ┌─────────────────────────────────────────┐
  │  Issue: E03-S02 冲突密度不足             │
  │  ───────────────────────────             │
  │  原文:                                    │
  │  "角色A: 今天的天气真不错啊...            │
  │   角色B: 是啊，适合出去走走...             │
  │   角色A: 你最近怎么样...                  │
  │   角色B: 还行吧，就那样..."               │
  │                                           │
  │  问题: 4个连续对白段无冲突推进              │
  │  建议修改: 在segment=4处插入...            │
  │                                           │
  │  [接受建议] [自己修改] [标记为故意设计]   │
  └─────────────────────────────────────────┘
```

---

## 附录 A: Agent 状态机

每个 Agent 实例有自己的生命周期状态：

```
                 ┌─────────┐
                 │  IDLE   │
                 └────┬────┘
                      │ receive_task
                      ▼
                 ┌─────────┐
                 │WORKING  │
                 └────┬────┘
                      │
            ┌─────────┼─────────┐
            │ submit   │ error   │ self_review
            ▼         ▼         ▼
       ┌─────────┐ ┌─────────┐ ┌──────────────┐
       │AWAITING │ │ FAILED  │ │ SELF_REVIEW  │
       │ REVIEW  │ └─────────┘ │ (optional)   │
       └────┬────┘             └──────┬───────┘
            │                         │
     ┌──────┼──────┐                  │ pass
     │      │      │                  ▼
     ▼      ▼      ▼            (goes to AWAITING REVIEW)
  ┌────┐ ┌────┐ ┌────┐
  │PASS│ │REVISE│ │REJECT│
  └──┬─┘ └──┬─┘ └──┬──┘
     │      │      │
     ▼      │      ▼
  (next     │   ┌──────┐
  stage)    │   │HUMAN │
            │   │DECIDE│
            │   └──────┘
            │
            └──→ WORKING (revision)
```

## 附录 B: 审查闭环追踪

所有 Agent 审查在 `review_history` 中留下完整痕迹：

```jsonc
{
  "review_history": [
    {
      "round": 1,
      "timestamp": "2026-08-07T10:00:00Z",
      "reviewer": { "agent_id": "drama_critic_v1", "agent_version": "1.2.0" },
      "verdict": "needs_revision",
      "total_score": 68,
      "dimension_scores": { "completeness": 85, "consistency": 70, "quality": 60, "executability": 75, "compliance": 90 },
      "issues": [{ "id": "ISSUE-001", "severity": "blocker", "category": "conflict_density", "location": "E03-S02" }],
      "revision_delta": null
    },
    {
      "round": 2,
      "timestamp": "2026-08-07T10:45:00Z",
      "reviewer": { "agent_id": "drama_critic_v1", "agent_version": "1.2.0" },
      "verdict": "approved_with_minor",
      "total_score": 82,
      "dimension_scores": { "completeness": 88, "consistency": 75, "quality": 80, "executability": 85, "compliance": 90 },
      "issues": [{ "id": "ISSUE-007", "severity": "minor", "category": "dialogue_repetition", "location": "E05-S03" }],
      "revision_delta": {
        "previous_version": 1,
        "scenes_modified": ["E03-S02", "E05-S01"],
        "scenes_added": 0,
        "scenes_removed": 0,
        "character_count_delta": 0,
        "total_duration_delta_ms": +5000,
        "resolved_issues": ["ISSUE-001", "ISSUE-002", "ISSUE-003"],
        "unresolved_issues": []
      }
    }
  ]
}
```

**可追溯性保证**：
- 可以回答"这个剧本修改为什么做了这个修改？" → 追溯到具体的 issue 和 agent
- 可以回答"这个 agent 的审查质量如何？" → 通过 revision_delta 查看它的建议是否被采纳
- 可以回答"哪个阶段最拖时间？" → 通过 timestamp 计算每个阶段的 wall time

---

## 附录 C: Multi-Agent 协作完整时序

以 Stage 1 Episode 3 为例：

```
T+0min   Orchestrator 分发任务: "ScriptWriter, 请生成 Episode 3 的一稿"
T+15min  ScriptWriter 完成 draft v1 → 提交
T+15min  Orchestrator 并行调度:
         → DramaCritic:   "请审查 Episode 3 v1 的叙事质量"
         → StyleGuard:    "请审查 Episode 3 v1 的风格调性"
T+20min  DramaCritic 完成 Review → 返回 3 blocker, 2 major
T+22min  StyleGuard 完成 Review → 返回 1 blocker, 1 major
T+22min  Orchestrator 合并审查意见:
         - dedup: 去重后 4 blocker (1个被两个 Agent 同时标记)
         - 4 blocker > 0 → verdict = needs_revision
T+22min  Orchestrator → ScriptWriter: "4个blocker问题需要修改"
T+35min  ScriptWriter 完成 revision → draft v2
T+35min  Orchestrator 再次并行调度审查...
T+40min  DramaCritic: 0 blocker, 1 major, total=82 → pass
T+41min  StyleGuard: 0 blocker, 0 major, total=88 → pass
T+41min  Orchestrator 合并: 0 blocker, total=82 ≥ 80
         → verdict = approved_with_minor
         → 触发 Human Checkpoint: "请确认 Episode 3 的剧本"
T+41min  (等待用户操作...)
T+45min  用户: "接受, 进入下一集"
T+45min  Orchestrator: 锁定 Episode 3, 进入 Episode 4
```
