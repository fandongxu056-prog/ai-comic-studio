# AI 漫剧创作平台 — 四阶段数据 Schema 设计

> **设计原则**
> - 每个阶段的 Output 即是下一阶段的 Input，形成严格的数据契约
> - 所有 Schema 使用 JSON Schema (draft-2020-12) 规范
> - `id` 字段贯穿全链路，实现可追溯性
> - `status` 字段支持状态机流转和中断恢复
> - `meta` 对象承载阶段特定的元数据

---

## 数据全链路视图

```
用户输入                   Stage 1 输出                Stage 2 输出              Stage 3 输出              Stage 4 输出
┌──────────┐            ┌──────────────┐           ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ 创意/小说 │  ────→    │  结构化剧本   │  ────→   │  角色/场景    │  ────→  │  分镜脚本    │  ────→  │  成品视频    │
│ 梗概/大纲 │           │  (script)     │          │  资产档案     │         │  (storyboard) │         │  (production)│
└──────────┘            └──────────────┘          └──────────────┘         └──────────────┘         └──────────────┘
      │                       │                         │                        │                       │
   creative_input         structured_script       asset_profiles           shot_plan              final_video
   .json                  .json                   .json                    .json                   .json
```

---

## Stage 0: 项目输入（用户侧）

在进入四个正式阶段之前，用户需要先定义项目的基本信息。

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/project-input.json",
  "title": "ProjectInput",
  "description": "用户创建项目时的初始输入",

  "type": "object",
  "required": ["project_id", "title", "source_type", "source_content"],

  "properties": {
    "project_id": {
      "type": "string",
      "description": "项目唯一标识，UUIDv7"
    },
    "title": {
      "type": "string",
      "maxLength": 200,
      "description": "作品标题"
    },

    "source_type": {
      "type": "string",
      "enum": ["original_idea", "novel_excerpt", "synopsis", "outline", "full_novel"],
      "description": "输入源类型"
    },
    "source_content": {
      "type": "string",
      "maxLength": 200000,
      "description": "输入源正文（创意描述/小说原文/梗概/大纲）"
    },
    "source_url": {
      "type": "string",
      "format": "uri",
      "description": "如果有在线原文，可提供链接（可选）"
    },

    "genre": {
      "type": "object",
      "description": "题材标签",
      "properties": {
        "primary": {
          "type": "string",
          "enum": ["romance", "fantasy", "sci_fi", "action", "horror", "comedy", "drama", "mystery", "historical", "xianxia", "wuxia", "urban", "other"]
        },
        "sub_tags": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 10,
          "description": "次级标签，如 ['重生', '逆袭', '甜宠']"
        }
      }
    },

    "target_spec": {
      "type": "object",
      "description": "目标规格",
      "required": ["format", "total_duration_seconds"],
      "properties": {
        "format": {
          "type": "string",
          "enum": ["horizontal_standard", "vertical_short", "square"],
          "default": "horizontal_standard",
          "description": "横屏标准 | 竖屏短剧 | 方形"
        },
        "aspect_ratio": {
          "type": "string",
          "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
          "default": "16:9"
        },
        "target_resolution": {
          "type": "string",
          "enum": ["1920x1080", "1080x1920", "1280x720", "720x1280"],
          "default": "1920x1080"
        },
        "total_duration_seconds": {
          "type": "integer",
          "minimum": 30,
          "maximum": 7200,
          "description": "目标总时长（秒）"
        },
        "episode_count": {
          "type": "integer",
          "minimum": 1,
          "maximum": 200,
          "default": 1
        },
        "duration_per_episode_seconds": {
          "type": "integer",
          "minimum": 30,
          "maximum": 600,
          "description": "单集目标时长（秒）"
        }
      }
    },

    "style_preference": {
      "type": "object",
      "description": "风格偏好",
      "properties": {
        "art_style": {
          "type": "string",
          "enum": ["anime", "realistic", "semi_realistic", "cartoon", "ink_wash", "chinese_ink", "comic_book", "illustration", "3d_render", "other"]
        },
        "color_palette": {
          "type": "string",
          "description": "色调方向，如 'warm_dark', 'bright_vivid', 'muted_pastel'"
        },
        "reference_images": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "url": { "type": "string", "format": "uri" },
              "label": { "type": "string" },
              "usage": { "type": "string", "enum": ["art_style", "character_design", "scene_mood", "color_reference"] }
            }
          },
          "maxItems": 20
        },
        "style_notes": {
          "type": "string",
          "maxLength": 2000,
          "description": "自由文本风格描述"
        }
      }
    },

    "model_preferences": {
      "type": "object",
      "description": "模型偏好（可选，不填则用默认）",
      "properties": {
        "text_model": { "type": "string" },
        "image_model": { "type": "string" },
        "video_model": { "type": "string" },
        "tts_model": { "type": "string" }
      }
    }
  }
}
```

---

## Stage 1: 剧本阶段 (Script)

```
┌──────────────┐     ┌─────────────────────────────────────┐     ┌──────────────────┐
│ ProjectInput │ ──→ │   Multi-Agent 剧本创作               │ ──→ │ StructuredScript │
│              │     │   编剧Agent → 剧评Agent → 风格Agent   │     │                  │
└──────────────┘     └─────────────────────────────────────┘     └──────────────────┘
```

### 阶段说明

这是创意密度最高的阶段。建议用 Multi-Agent 协作：
- **编剧 Agent**：负责剧本生成/改编
- **剧评 Agent**：从节奏、冲突、人物弧光角度审视
- **风格 Agent**：把控题材一致性、台词风格

### Input Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage1-script-input.json",
  "title": "Stage1ScriptInput",
  "description": "剧本阶段的输入——即项目初始化信息 + 用户确认的创作方向",

  "type": "object",
  "required": ["project_id", "source_material", "creative_direction"],

  "properties": {
    "project_id": {
      "type": "string",
      "description": "关联的项目 ID"
    },

    "source_material": {
      "type": "object",
      "description": "源材料（从 ProjectInput 提取并预处理后的版本）",
      "required": ["type", "raw_text"],
      "properties": {
        "type": { "$ref": "#/properties/source_type" },
        "raw_text": { "type": "string" },
        "word_count": { "type": "integer" },
        "extracted_characters": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "mentions_count": { "type": "integer" },
              "first_appearance_context": { "type": "string" },
              "role_hint": { "type": "string", "enum": ["protagonist", "antagonist", "supporting", "cameo", "unknown"] }
            }
          },
          "description": "从原文预提取的角色列表（供剧本Agent参考）"
        },
        "extracted_locations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "mentions_count": { "type": "integer" },
              "description_fragments": {
                "type": "array",
                "items": { "type": "string" }
              }
            }
          },
          "description": "从原文预提取的场景/地点列表"
        }
      }
    },

    "creative_direction": {
      "type": "object",
      "description": "创作方向（用户确认/调整后的策略）",
      "required": ["adaptation_strategy"],
      "properties": {
        "adaptation_strategy": {
          "type": "string",
          "enum": ["faithful", "loose_adaptation", "reimagine", "original_creation"],
          "description": "忠实改编 | 宽松改编 | 重构想象 | 原创"
        },
        "narrative_tone": {
          "type": "string",
          "description": "叙事基调：快节奏/慢热/爽文/虐心/轻松/暗黑 等"
        },
        "target_emotion_curve": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "episode": { "type": "integer" },
              "emotion": { "type": "string" },
              "intensity": { "type": "integer", "minimum": 1, "maximum": 10 }
            }
          },
          "description": "目标情绪曲线（可选，用于长剧集的整体把控）"
        },
        "key_themes": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 10
        },
        "avoid_elements": {
          "type": "array",
          "items": { "type": "string" },
          "description": "需要规避的元素"
        },
        "special_requirements": {
          "type": "string",
          "maxLength": 2000
        }
      }
    },

    "previous_stage_output": {
      "description": "如果是回退修改场景，携带上一版的 Stage 1 输出 + 修改意见",
      "type": "object",
      "properties": {
        "previous_script": { "$ref": "#/..." },
        "revision_notes": { "type": "string" }
      }
    }
  }
}
```

### Output Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage1-script-output.json",
  "title": "StructuredScript",
  "description": "剧本阶段的输出——结构化剧本，是后续所有阶段的"单一事实来源"",

  "type": "object",
  "required": ["script_id", "project_id", "version", "created_at", "episodes", "global_context"],

  "properties": {
    "script_id": {
      "type": "string",
      "description": "剧本唯一 ID"
    },
    "project_id": { "type": "string" },
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "版本号，每次修改递增"
    },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "status": {
      "type": "string",
      "enum": ["draft", "review", "approved", "locked"],
      "description": "draft=编辑中 | review=待审 | approved=通过 | locked=已锁定（后续阶段已基于此版本开始工作）"
    },

    "global_context": {
      "type": "object",
      "description": "全局语境——跨集共享的故事世界观信息",
      "required": ["story_world", "power_system", "timeline"],
      "properties": {
        "story_world": {
          "type": "object",
          "properties": {
            "setting": { "type": "string", "description": "世界观设定描述" },
            "era": { "type": "string", "description": "时代背景" },
            "rules": { "type": "array", "items": { "type": "string" }, "description": "世界观规则" }
          }
        },
        "power_system": {
          "type": "object",
          "description": "力量体系（仙侠/玄幻类尤其重要）",
          "properties": {
            "name": { "type": "string" },
            "levels": { "type": "array", "items": { "type": "string" } },
            "rules": { "type": "string" }
          }
        },
        "timeline": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "event_id": { "type": "string" },
              "description": { "type": "string" },
              "episode_ref": { "type": "integer" },
              "is_major": { "type": "boolean" }
            }
          },
          "description": "关键事件时间线"
        },
        "continuity_rules": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "rule_id": { "type": "string" },
              "category": { "type": "string", "enum": ["character_trait", "relationship", "item_state", "location_state", "power_level"] },
              "description": { "type": "string" },
              "scope": { "type": "string", "enum": ["global", "episode_range"] },
              "episode_range": { "type": "array", "items": { "type": "integer" } }
            }
          },
          "description": "连续性规则——跨集的约束条件"
        }
      }
    },

    "episodes": {
      "type": "array",
      "minItems": 1,
      "maxItems": 200,
      "items": {
        "type": "object",
        "required": ["episode_index", "title", "scenes"],
        "properties": {
          "episode_index": { "type": "integer", "minimum": 1 },
          "title": { "type": "string", "maxLength": 200 },
          "hook": {
            "type": "string",
            "maxLength": 500,
            "description": "本集钩子——开头吸引观众的一句话"
          },
          "cliffhanger": {
            "type": "string",
            "maxLength": 500,
            "description": "本集悬念——结尾留钩子"
          },
          "summary": {
            "type": "string",
            "maxLength": 1000,
            "description": "本集概要"
          },

          "scenes": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["scene_id", "scene_index", "location", "characters_present", "content"],
              "properties": {
                "scene_id": {
                  "type": "string",
                  "pattern": "^SC-[Ee]\\d{3}-S\\d{3}$",
                  "description": "场景 ID，如 SC-E001-S003"
                },
                "scene_index": { "type": "integer", "minimum": 1 },
                "location": {
                  "type": "object",
                  "required": ["name"],
                  "properties": {
                    "name": { "type": "string" },
                    "time_of_day": { "type": "string", "enum": ["dawn", "morning", "noon", "afternoon", "evening", "night", "midnight", "unspecified"] },
                    "weather": { "type": "string" },
                    "mood": { "type": "string" },
                    "description": { "type": "string", "maxLength": 1000 }
                  }
                },
                "characters_present": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["character_ref"],
                    "properties": {
                      "character_ref": { "type": "string", "description": "角色引用名（后续 Stage 2 会关联到正式角色档案）" },
                      "emotional_state": { "type": "string" },
                      "costume_note": { "type": "string" },
                      "appearance_note": { "type": "string", "description": "本场特殊外貌变化"}
                    }
                  }
                },
                "props_mentioned": {
                  "type": "array",
                  "items": { "type": "string" },
                  "description": "本场涉及的道具"
                },
                "content": {
                  "type": "object",
                  "description": "场景内容——剧本的核心",
                  "required": ["segments"],
                  "properties": {
                    "segments": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["type", "text"],
                        "properties": {
                          "type": {
                            "type": "string",
                            "enum": ["narration", "dialogue", "action", "inner_monologue", "voice_over", "transition"]
                          },
                          "character_ref": {
                            "type": "string",
                            "description": "说话人引用（dialogue/inner_monologue 时必填）"
                          },
                          "text": { "type": "string" },
                          "emotion_tag": { "type": "string", "description": "情绪标签，如 '愤怒', '冷笑', '哽咽'" },
                          "action_tag": { "type": "string", "description": "动作标注，如 '拔剑', '转身', '摔门'" },
                          "duration_hint_ms": {
                            "type": "integer",
                            "minimum": 500,
                            "description": "预估时长（毫秒），用于后续分镜时长计算"
                          }
                        }
                      }
                    },
                    "scene_duration_estimate_ms": { "type": "integer" }
                  }
                },
                "visual_emphasis": {
                  "type": "array",
                  "items": { "type": "string" },
                  "description": "本场需要视觉强调的元素（情感爆点、关键道具、特殊效果）"
                }
              }
            }
          }
        }
      }
    },

    "character_index": {
      "type": "object",
      "description": "剧本角色索引——从所有场景中汇总出的角色清单，作为 Stage 2 的输入",
      "properties": {
        "characters": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["ref_name", "role_type"],
            "properties": {
              "ref_name": { "type": "string" },
              "full_name": { "type": "string" },
              "role_type": { "type": "string", "enum": ["protagonist", "antagonist", "supporting", "cameo"] },
              "scene_count": { "type": "integer" },
              "dialogue_count": { "type": "integer" },
              "first_episode": { "type": "integer" },
              "traits_from_script": { "type": "array", "items": { "type": "string" } },
              "relationships": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "with_character": { "type": "string" },
                    "relationship_type": { "type": "string" }
                  }
                }
              }
            }
          }
        }
      }
    },

    "location_index": {
      "type": "object",
      "description": "剧本场景索引——汇总所有场景地点",
      "properties": {
        "locations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name"],
            "properties": {
              "name": { "type": "string" },
              "scene_count": { "type": "integer" },
              "variations": { "type": "array", "items": { "type": "string" }, "description": "不同时间/天气的变化" }
            }
          }
        }
      }
    },

    "prop_index": {
      "type": "object",
      "description": "道具索引——汇总所有场景中出现的道具",
      "properties": {
        "props": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name"],
            "properties": {
              "name": { "type": "string" },
              "scene_count": { "type": "integer" },
              "importance": { "type": "string", "enum": ["key_item", "recurring", "one_off"] },
              "description_from_script": { "type": "string" }
            }
          }
        }
      }
    },

    "review_history": {
      "type": "array",
      "description": "审查记录（Multi-Agent 对话的摘要）",
      "items": {
        "type": "object",
        "properties": {
          "round": { "type": "integer" },
          "reviewer": { "type": "string", "enum": ["drama_critic_agent", "style_agent", "human"] },
          "verdict": { "type": "string", "enum": ["approved", "needs_revision", "rejected"] },
          "comments": { "type": "string" },
          "resolved": { "type": "boolean" }
        }
      }
    }
  }
}
```

---

## Stage 2: 角色/场景设计阶段 (Asset Design)

```
┌──────────────────┐     ┌──────────────────────────────────┐     ┌──────────────────┐
│ StructuredScript │ ──→ │   Multi-Agent 资产设计             │ ──→ │ AssetProfiles    │
│                  │     │   角色Agent → 场景Agent → 审查Agent │     │ + 参考图         │
└──────────────────┘     └──────────────────────────────────┘     └──────────────────┘
```

### 阶段说明

从剧本中提取的角色、场景、道具在此阶段被"具象化"。每个资产需要产出可复用的视觉定义。
- **角色设计 Agent**：基于剧本描述 + 风格偏好，产出角色视觉设计
- **场景设计 Agent**：基于地点索引，产出场景视觉设计
- **一致性审查 Agent**：检查角色之间、角色与场景之间的风格统一性

### Input Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage2-asset-input.json",
  "title": "Stage2AssetInput",
  "description": "资产设计阶段的输入",

  "type": "object",
  "required": ["project_id", "script_id", "character_index", "location_index", "prop_index", "style_preference"],

  "properties": {
    "project_id": { "type": "string" },
    "script_id": { "type": "string" },
    "script_version": { "type": "integer", "description": "基于哪个版本的剧本" },

    "character_index": {
      "$ref": "stage1-script-output.json#/properties/character_index"
    },
    "location_index": {
      "$ref": "stage1-script-output.json#/properties/location_index"
    },
    "prop_index": {
      "$ref": "stage1-script-output.json#/properties/prop_index"
    },

    "style_preference": {
      "description": "继承自 ProjectInput 的风格偏好",
      "type": "object",
      "properties": {
        "art_style": { "type": "string" },
        "color_palette": { "type": "string" },
        "reference_images": { "type": "array" }
      }
    },

    "consistency_requirements": {
      "type": "object",
      "description": "一致性要求（从剧本 continuity_rules 提取的相关部分）",
      "properties": {
        "global_style_seed": { "type": "integer", "description": "全局风格种子" },
        "character_style_notes": { "type": "string" },
        "scene_style_notes": { "type": "string" }
      }
    },

    "previous_stage_output": {
      "type": "object",
      "description": "回退修改场景",
      "properties": {
        "previous_assets": {},
        "revision_notes": { "type": "string" }
      }
    }
  }
}
```

### Output Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage2-asset-output.json",
  "title": "AssetProfiles",
  "description": "资产设计阶段的输出——角色/场景/道具的完整视觉档案",

  "type": "object",
  "required": ["asset_set_id", "project_id", "script_id", "version", "characters", "locations", "props", "style_manifest"],

  "properties": {
    "asset_set_id": { "type": "string" },
    "project_id": { "type": "string" },
    "script_id": { "type": "string" },
    "script_version": { "type": "integer" },
    "version": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "status": { "type": "string", "enum": ["draft", "review", "approved", "locked"] },

    "style_manifest": {
      "type": "object",
      "description": "风格清单——全项目统一的视觉风格定义",
      "required": ["art_style", "global_style_seed"],
      "properties": {
        "art_style": { "type": "string" },
        "global_style_seed": { "type": "integer", "description": "全局种子，用于生图一致性" },
        "color_palette": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "primary_colors": { "type": "array", "items": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" }, "maxItems": 5 },
            "accent_colors": { "type": "array", "items": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" }, "maxItems": 3 },
            "mood_colors": {
              "type": "object",
              "description": "场景情绪色彩映射",
              "properties": {
                "happy": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
                "sad": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
                "tense": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
                "romantic": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
                "dark": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" }
              }
            }
          }
        },
        "line_style": {
          "type": "string",
          "enum": ["clean", "sketchy", "bold", "delicate", "none"],
          "description": "线条风格（非3D渲染类需关注）"
        },
        "lighting_default": { "type": "string" },
        "global_negative_prompt": {
          "type": "string",
          "maxLength": 2000,
          "description": "全局负向提示词，生图时自动附加"
        }
      }
    },

    "characters": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["character_id", "ref_name", "design_sheet"],
        "properties": {
          "character_id": { "type": "string", "pattern": "^CHAR-\\d{4}$" },
          "ref_name": { "type": "string", "description": "与剧本中的 character_ref 对应" },
          "full_name": { "type": "string" },
          "role_type": { "type": "string", "enum": ["protagonist", "antagonist", "supporting", "cameo"] },

          "design_sheet": {
            "type": "object",
            "description": "角色设计表",
            "required": ["appearance", "costumes", "expressions"],
            "properties": {
              "appearance": {
                "type": "object",
                "required": ["age_appearance", "gender", "body_type", "face", "hair", "distinguishing_features"],
                "properties": {
                  "age_appearance": { "type": "string", "description": "视觉年龄范围，如 '20-25岁'" },
                  "gender": { "type": "string" },
                  "height_cm": { "type": "integer" },
                  "body_type": { "type": "string" },
                  "face": {
                    "type": "object",
                    "properties": {
                      "shape": { "type": "string" },
                      "eyes": { "type": "string" },
                      "nose": { "type": "string" },
                      "mouth": { "type": "string" },
                      "skin_tone": { "type": "string" },
                      "overall_description": { "type": "string" }
                    }
                  },
                  "hair": {
                    "type": "object",
                    "properties": {
                      "color": { "type": "string" },
                      "style": { "type": "string" },
                      "length": { "type": "string" }
                    }
                  },
                  "distinguishing_features": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "识别特征（疤痕、配饰、特殊标记等）"
                  }
                }
              },

              "costumes": {
                "type": "array",
                "minItems": 1,
                "items": {
                  "type": "object",
                  "required": ["costume_id", "name", "description"],
                  "properties": {
                    "costume_id": { "type": "string", "pattern": "^COST-\\d{4}$" },
                    "name": { "type": "string" },
                    "description": { "type": "string" },
                    "scenes_used_in": {
                      "type": "array",
                      "items": { "type": "string" },
                      "description": "该服装出现的场景 ID 列表"
                    },
                    "color_palette": { "type": "array", "items": { "type": "string" } },
                    "accessories": { "type": "array", "items": { "type": "string" } },
                    "season": { "type": "string" }
                  }
                }
              },

              "expressions": {
                "type": "object",
                "description": "关键表情包定义",
                "properties": {
                  "neutral": { "type": "string", "description": "默认表情描述" },
                  "happy": { "type": "string" },
                  "angry": { "type": "string" },
                  "sad": { "type": "string" },
                  "surprised": { "type": "string" },
                  "scheming": { "type": "string" },
                  "cold": { "type": "string" }
                }
              },

              "pose_notes": {
                "type": "string",
                "description": "角色体态/站姿特征"
              }
            }
          },

          "reference_images": {
            "type": "object",
            "description": "角色参考图（生成后的 URL）",
            "properties": {
              "full_body_front": { "type": "string", "format": "uri" },
              "full_body_back": { "type": "string", "format": "uri" },
              "portrait": { "type": "string", "format": "uri" },
              "expression_sheet": { "type": "string", "format": "uri" },
              "costume_variants": {
                "type": "object",
                "additionalProperties": { "type": "string", "format": "uri" }
              }
            }
          },

          "character_prompt_template": {
            "type": "string",
            "description": "该角色的稳定生图提示词模板（注入到每个分镜生成中）",
            "maxLength": 3000
          },

          "voice_profile": {
            "type": "object",
            "description": "配音配置（为 Stage 4 准备）",
            "properties": {
              "gender": { "type": "string" },
              "age_range": { "type": "string" },
              "tone": { "type": "string" },
              "pace": { "type": "string" },
              "tts_voice_id": { "type": "string" }
            }
          }
        }
      }
    },

    "locations": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["location_id", "name", "design_sheet"],
        "properties": {
          "location_id": { "type": "string", "pattern": "^LOC-\\d{4}$" },
          "name": { "type": "string" },
          "design_sheet": {
            "type": "object",
            "required": ["description", "key_features", "variations"],
            "properties": {
              "description": { "type": "string", "description": "场景空间描述" },
              "key_features": {
                "type": "array",
                "items": { "type": "string" },
                "description": "关键视觉特征（用于生图一致性）"
              },
              "layout_notes": {
                "type": "string",
                "description": "空间布局说明（人物通常站在哪、有什么遮挡物等）"
              },
              "variations": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["variation_id", "condition"],
                  "properties": {
                    "variation_id": { "type": "string" },
                    "condition": { "type": "string", "description": "如 'night', 'rain', 'destroyed'" },
                    "description_modifier": { "type": "string" }
                  }
                }
              }
            }
          },
          "reference_images": {
            "type": "object",
            "properties": {
              "wide_establishing": { "type": "string", "format": "uri" },
              "medium_angle": { "type": "string", "format": "uri" },
              "detail_shots": {
                "type": "array",
                "items": { "type": "string", "format": "uri" }
              }
            }
          },
          "location_prompt_template": {
            "type": "string",
            "maxLength": 3000
          }
        }
      }
    },

    "props": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["prop_id", "name", "design"],
        "properties": {
          "prop_id": { "type": "string", "pattern": "^PROP-\\d{4}$" },
          "name": { "type": "string" },
          "importance": { "type": "string", "enum": ["key_item", "recurring", "one_off"] },
          "design": {
            "type": "object",
            "required": ["description"],
            "properties": {
              "description": { "type": "string" },
              "material": { "type": "string" },
              "color": { "type": "string" },
              "size_hint": { "type": "string" },
              "special_effects": { "type": "string" }
            }
          },
          "reference_image": { "type": "string", "format": "uri" },
          "prop_prompt_template": { "type": "string", "maxLength": 2000 }
        }
      }
    },

    "consistency_cross_reference": {
      "type": "object",
      "description": "跨资产一致性引用表——用于 Stage 3/4 快速查找",
      "properties": {
        "character_scene_map": {
          "type": "object",
          "description": "角色 → 出现的场景",
          "additionalProperties": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "scene_character_map": {
          "type": "object",
          "description": "场景 → 出现的角色",
          "additionalProperties": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "prop_scene_map": {
          "type": "object",
          "description": "道具 → 出现的场景"
        }
      }
    },

    "review_history": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "round": { "type": "integer" },
          "reviewer": { "type": "string", "enum": ["consistency_agent", "style_agent", "human"] },
          "verdict": { "type": "string", "enum": ["approved", "needs_revision", "rejected"] },
          "comments": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Stage 3: 分镜阶段 (Storyboard)

```
┌──────────────────┐     ┌────────────────────────────────┐     ┌──────────────────┐
│ StructuredScript │     │   Multi-Agent 分镜设计           │     │ ShotPlan         │
│ + AssetProfiles  │ ──→ │   分镜Agent → 节奏Agent → 审查   │ ──→ │ + 关键帧提示词    │
└──────────────────┘     └────────────────────────────────┘     └──────────────────┘
```

### 阶段说明

将剧本 + 资产档案转化为可执行的分镜脚本。这是"创意"到"执行"的关键桥梁。
- **分镜 Agent**：逐场景拆解为镜头，定义景别、角度、运镜
- **节奏 Agent**：检查镜头时长分配、叙事节奏
- **一致性 Agent**：验证角色/场景引用正确、连续性规则遵守

### Input Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage3-storyboard-input.json",
  "title": "Stage3StoryboardInput",
  "description": "分镜阶段的输入——剧本 + 资产档案",

  "type": "object",
  "required": ["project_id", "script", "assets", "target_spec"],

  "properties": {
    "project_id": { "type": "string" },
    "script_id": { "type": "string" },
    "asset_set_id": { "type": "string" },

    "script": {
      "type": "object",
      "description": "需要分镜的剧本范围（可按集/按场景筛选）",
      "required": ["episodes"],
      "properties": {
        "episodes": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["episode_index"],
            "properties": {
              "episode_index": { "type": "integer" },
              "scene_ids": {
                "type": "array",
                "items": { "type": "string" },
                "description": "指定场景范围（空数组 = 全集所有场景）"
              }
            }
          }
        }
      }
    },

    "assets": {
      "type": "object",
      "description": "资产档案引用（从 Stage 2 输出中提取）",
      "required": ["style_manifest", "characters", "locations", "props"],
      "properties": {
        "style_manifest": { "type": "object" },
        "characters": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "required": ["character_id", "ref_name", "character_prompt_template", "reference_images", "costumes"],
            "properties": {
              "character_id": { "type": "string" },
              "ref_name": { "type": "string" },
              "character_prompt_template": { "type": "string" },
              "reference_images": { "type": "object" },
              "costumes": { "type": "array" }
            }
          }
        },
        "locations": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "required": ["location_id", "name", "location_prompt_template", "reference_images"],
            "properties": {
              "location_id": { "type": "string" },
              "name": { "type": "string" },
              "location_prompt_template": { "type": "string" },
              "reference_images": { "type": "object" }
            }
          }
        },
        "props": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "required": ["prop_id", "name", "prop_prompt_template"],
            "properties": {
              "prop_id": { "type": "string" },
              "name": { "type": "string" },
              "prop_prompt_template": { "type": "string" }
            }
          }
        }
      }
    },

    "target_spec": {
      "type": "object",
      "description": "目标规格（继承自 ProjectInput）",
      "required": ["episode_duration_seconds", "aspect_ratio"],
      "properties": {
        "episode_duration_seconds": { "type": "integer" },
        "aspect_ratio": { "type": "string" }
      }
    },

    "continuity_rules": {
      "type": "array",
      "description": "从剧本中提取的连续性规则"
    },

    "previous_stage_output": {
      "type": "object",
      "properties": {
        "previous_storyboard": {},
        "revision_notes": { "type": "string" }
      }
    }
  }
}
```

### Output Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage3-storyboard-output.json",
  "title": "ShotPlan",
  "description": "分镜阶段的输出——可执行的分镜脚本，每个镜头包含画面提示词、时长、转场等完整信息",

  "type": "object",
  "required": ["storyboard_id", "project_id", "script_id", "asset_set_id", "version", "episodes"],

  "properties": {
    "storyboard_id": { "type": "string" },
    "project_id": { "type": "string" },
    "script_id": { "type": "string" },
    "asset_set_id": { "type": "string" },
    "version": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "status": { "type": "string", "enum": ["draft", "review", "approved", "locked"] },

    "episodes": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["episode_index", "scenes"],
        "properties": {
          "episode_index": { "type": "integer" },
          "title": { "type": "string" },
          "estimated_duration_ms": { "type": "integer" },

          "scenes": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["scene_id", "shots"],
              "properties": {
                "scene_id": { "type": "string" },
                "location_id": { "type": "string" },
                "scene_mood": { "type": "string" },

                "shots": {
                  "type": "array",
                  "minItems": 1,
                  "items": {
                    "type": "object",
                    "required": ["shot_id", "shot_index", "shot_type", "duration_ms", "keyframe", "dialogue"],

                    "properties": {
                      "shot_id": {
                        "type": "string",
                        "pattern": "^SH-E\\d{3}-S\\d{3}-\\d{3}$",
                        "description": "镜头 ID，如 SH-E001-S003-005"
                      },
                      "shot_index": { "type": "integer" },

                      // ── 镜头规格 ──
                      "shot_type": {
                        "type": "string",
                        "enum": [
                          "extreme_close_up", "close_up", "medium_close_up",
                          "medium_shot", "medium_full_shot", "full_shot",
                          "long_shot", "extreme_long_shot",
                          "over_shoulder", "pov", "dutch_angle", "aerial"
                        ],
                        "description": "景别"
                      },
                      "camera_angle": {
                        "type": "string",
                        "enum": ["eye_level", "low_angle", "high_angle", "birds_eye", "worms_eye", "dutch"],
                        "default": "eye_level"
                      },
                      "camera_movement": {
                        "type": "object",
                        "properties": {
                          "type": {
                            "type": "string",
                            "enum": ["static", "pan_left", "pan_right", "tilt_up", "tilt_down", "zoom_in", "zoom_out", "dolly_in", "dolly_out", "track_left", "track_right", "arc", "handheld"]
                          },
                          "intensity": {
                            "type": "string",
                            "enum": ["subtle", "moderate", "dramatic"]
                          },
                          "duration_fraction": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "运镜占镜头时长的比例，0.3 = 前30%完成运镜"
                          }
                        }
                      },

                      "duration_ms": {
                        "type": "integer",
                        "minimum": 500,
                        "maximum": 30000
                      },

                      // ── 画面内容 ──
                      "keyframe": {
                        "type": "object",
                        "description": "关键帧定义",
                        "required": ["composition", "image_prompt"],
                        "properties": {
                          "composition": {
                            "type": "object",
                            "description": "构图描述",
                            "required": ["subject_focus"],
                            "properties": {
                              "subject_focus": {
                                "type": "string",
                                "description": "画面焦点（角色/物体/场景）"
                              },
                              "foreground": { "type": "string" },
                              "midground": { "type": "string" },
                              "background": { "type": "string" },
                              "depth_of_field": {
                                "type": "string",
                                "enum": ["shallow", "medium", "deep"]
                              },
                              "rule_of_thirds_position": {
                                "type": "string",
                                "enum": ["center", "left_third", "right_third", "top_third", "bottom_third"]
                              }
                            }
                          },
                          "characters_in_frame": {
                            "type": "array",
                            "items": {
                              "type": "object",
                              "required": ["character_id", "costume_id"],
                              "properties": {
                                "character_id": { "type": "string" },
                                "costume_id": { "type": "string" },
                                "pose": { "type": "string" },
                                "expression": { "type": "string" },
                                "position_in_frame": { "type": "string" },
                                "action": { "type": "string" }
                              }
                            }
                          },
                          "props_in_frame": {
                            "type": "array",
                            "items": {
                              "type": "object",
                              "properties": {
                                "prop_id": { "type": "string" },
                                "position_in_frame": { "type": "string" },
                                "state": { "type": "string" }
                              }
                            }
                          },

                          // ── 核心：生图提示词 ──
                          "image_prompt": {
                            "type": "object",
                            "required": ["positive", "negative"],
                            "properties": {
                              "positive": {
                                "type": "string",
                                "maxLength": 4000,
                                "description": "正向提示词（英文，已注入角色/场景模板）"
                              },
                              "negative": {
                                "type": "string",
                                "maxLength": 2000,
                                "description": "负向提示词"
                              },
                              "seed": {
                                "type": "integer",
                                "description": "种子（继承全局种子 + 镜头偏移）"
                              },
                              "model_params": {
                                "type": "object",
                                "description": "模型特定参数",
                                "properties": {
                                  "cfg_scale": { "type": "number", "minimum": 1, "maximum": 30 },
                                  "steps": { "type": "integer", "minimum": 10, "maximum": 100 },
                                  "width": { "type": "integer" },
                                  "height": { "type": "integer" }
                                }
                              }
                            }
                          },

                          // ── 视频提示词（如果需要首尾帧视频生成） ──
                          "video_prompt": {
                            "type": "object",
                            "properties": {
                              "start_frame_prompt": { "type": "string", "maxLength": 2000 },
                              "end_frame_prompt": { "type": "string", "maxLength": 2000 },
                              "motion_description": { "type": "string", "maxLength": 1000 },
                              "motion_strength": { "type": "number", "minimum": 0, "maximum": 1 }
                            }
                          }
                        }
                      },

                      // ── 对白/字幕 ──
                      "dialogue": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "required": ["character_id", "text", "start_ms", "end_ms"],
                          "properties": {
                            "character_id": { "type": "string" },
                            "text": { "type": "string" },
                            "start_ms": { "type": "integer" },
                            "end_ms": { "type": "integer" },
                            "emotion": { "type": "string" },
                            "delivery_notes": { "type": "string", "description": "配音指导（语速、语气等）" }
                          }
                        }
                      },

                      // ── 音效/配乐提示 ──
                      "audio_notes": {
                        "type": "object",
                        "properties": {
                          "bgm": { "type": "string", "description": "背景音乐风格/情绪" },
                          "sfx": {
                            "type": "array",
                            "items": {
                              "type": "object",
                              "properties": {
                                "description": { "type": "string" },
                                "timing_ms": { "type": "integer" }
                              }
                            }
                          },
                          "ambient": { "type": "string", "description": "环境音" }
                        }
                      },

                      // ── 转场 ──
                      "transition": {
                        "type": "object",
                        "properties": {
                          "from_previous": {
                            "type": "string",
                            "enum": ["cut", "fade_in", "fade_out", "crossfade", "wipe_left", "wipe_right", "slide", "zoom_transition", "none"],
                            "default": "cut"
                          },
                          "transition_duration_ms": { "type": "integer", "default": 0 },
                          "transition_notes": { "type": "string" }
                        }
                      },

                      // ── 特效标注 ──
                      "vfx_notes": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "effect_type": {
                              "type": "string",
                              "enum": ["speed_lines", "impact_flash", "light_rays", "particles", "glow", "shake", "blur", "color_grade", "text_overlay"]
                            },
                            "description": { "type": "string" },
                            "timing_ms": { "type": "integer" }
                          }
                        }
                      },

                      "reference_shot_ids": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "引用镜头 ID（风格/构图参考）"
                      }
                    }
                  }
                },

                "scene_shot_count": { "type": "integer" },
                "scene_total_duration_ms": { "type": "integer" }
              }
            }
          },

          "episode_total_duration_ms": { "type": "integer" },
          "episode_shot_count": { "type": "integer" }
        }
      }
    },

    "tempo_analysis": {
      "type": "object",
      "description": "节奏分析（节奏 Agent 的输出）",
      "properties": {
        "shot_duration_distribution": {
          "type": "object",
          "properties": {
            "ultra_short_count": { "type": "integer", "description": "<1s 镜头数" },
            "short_count": { "type": "integer", "description": "1-2s" },
            "medium_count": { "type": "integer", "description": "2-5s" },
            "long_count": { "type": "integer", "description": "5-10s" },
            "ultra_long_count": { "type": "integer", "description": ">10s" }
          }
        },
        "pacing_curve": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "shot_index": { "type": "integer" },
              "tension_level": { "type": "integer", "minimum": 1, "maximum": 10 },
              "note": { "type": "string" }
            }
          }
        },
        "warnings": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "severity": { "type": "string", "enum": ["info", "warning", "critical"] },
              "shot_id": { "type": "string" },
              "message": { "type": "string" }
            }
          }
        }
      }
    },

    "review_history": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "round": { "type": "integer" },
          "reviewer": { "type": "string", "enum": ["storyboard_agent", "pacing_agent", "consistency_agent", "human"] },
          "verdict": { "type": "string" },
          "comments": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Stage 4: 制作阶段 (Production)

```
┌──────────────────┐     ┌──────────────────────────────────┐     ┌──────────────────┐
│ ShotPlan         │     │   Pipeline 确定性执行              │     │ FinalVideo       │
│ + AssetProfiles  │ ──→ │   生图→动画→配音→合成→导出         │ ──→ │ + 项目归档       │
└──────────────────┘     └──────────────────────────────────┘     └──────────────────┘
```

### 阶段说明

这是唯一的**确定性 Pipeline 阶段**，不需要 Agent 创意协作。按分镜脚本逐镜头执行：
1. 图片生成（可并行）
2. 视频生成/动画（可并行）
3. 配音生成（可并行）
4. 音频后期
5. 剪辑合成
6. 导出

### Input Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage4-production-input.json",
  "title": "Stage4ProductionInput",
  "description": "制作阶段的输入——分镜脚本 + 资产档案 + 生成配置",

  "type": "object",
  "required": ["project_id", "shot_plan", "asset_references", "generation_config"],

  "properties": {
    "project_id": { "type": "string" },
    "storyboard_id": { "type": "string" },
    "asset_set_id": { "type": "string" },

    "shot_plan": {
      "type": "object",
      "description": "完整分镜脚本（Stage 3 输出）",
      "required": ["episodes"],
      "properties": {
        "episodes": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["episode_index", "scenes"],
            "properties": {
              "episode_index": { "type": "integer" },
              "scenes": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["scene_id", "shots"],
                  "properties": {
                    "scene_id": { "type": "string" },
                    "shots": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["shot_id", "keyframe", "dialogue", "duration_ms"],
                        "properties": {
                          "shot_id": { "type": "string" },
                          "duration_ms": { "type": "integer" },
                          "keyframe": {
                            "type": "object",
                            "required": ["image_prompt"],
                            "properties": {
                              "image_prompt": {
                                "type": "object",
                                "required": ["positive", "negative"],
                                "properties": {
                                  "positive": { "type": "string" },
                                  "negative": { "type": "string" },
                                  "seed": { "type": "integer" },
                                  "model_params": { "type": "object" }
                                }
                              },
                              "video_prompt": { "type": "object" }
                            }
                          },
                          "dialogue": { "type": "array" },
                          "audio_notes": { "type": "object" },
                          "transition": { "type": "object" },
                          "vfx_notes": { "type": "array" }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },

    "asset_references": {
      "type": "object",
      "description": "资产文件引用（URL 列表）",
      "properties": {
        "character_images": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "full_body_front": { "type": "string", "format": "uri" },
              "portrait": { "type": "string", "format": "uri" },
              "expression_sheet": { "type": "string", "format": "uri" }
            }
          }
        },
        "location_images": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "wide_establishing": { "type": "string", "format": "uri" }
            }
          }
        },
        "prop_images": {
          "type": "object",
          "additionalProperties": {
            "type": "string", "format": "uri"
          }
        }
      }
    },

    "generation_config": {
      "type": "object",
      "description": "生成配置——控制 Pipeline 行为",
      "required": ["image_generation", "video_generation", "tts_generation"],
      "properties": {
        "image_generation": {
          "type": "object",
          "required": ["provider", "model"],
          "properties": {
            "provider": { "type": "string" },
            "model": { "type": "string" },
            "concurrency": { "type": "integer", "default": 4, "description": "并行度" },
            "retry_count": { "type": "integer", "default": 3 },
            "timeout_seconds": { "type": "integer", "default": 120 },
            "output_format": { "type": "string", "enum": ["png", "jpg", "webp"], "default": "png" }
          }
        },
        "video_generation": {
          "type": "object",
          "required": ["provider", "model"],
          "properties": {
            "provider": { "type": "string" },
            "model": { "type": "string" },
            "fps": { "type": "integer", "default": 24 },
            "motion_strength": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.7 },
            "concurrency": { "type": "integer", "default": 2 },
            "retry_count": { "type": "integer", "default": 2 },
            "timeout_seconds": { "type": "integer", "default": 300 }
          }
        },
        "tts_generation": {
          "type": "object",
          "required": ["provider", "model"],
          "properties": {
            "provider": { "type": "string" },
            "model": { "type": "string" },
            "default_voice_id": { "type": "string" },
            "language": { "type": "string", "default": "zh-CN" },
            "concurrency": { "type": "integer", "default": 2 },
            "retry_count": { "type": "integer", "default": 2 }
          }
        },
        "compositing": {
          "type": "object",
          "properties": {
            "engine": { "type": "string", "enum": ["ffmpeg", "remotion"], "default": "ffmpeg" },
            "output_format": { "type": "string", "enum": ["mp4", "mov", "webm"], "default": "mp4" },
            "output_codec": { "type": "string", "default": "h264" },
            "include_subtitles": { "type": "boolean", "default": true },
            "subtitle_style": { "type": "string", "default": "default" },
            "watermark": {
              "type": "object",
              "properties": {
                "enabled": { "type": "boolean", "default": false },
                "text": { "type": "string" },
                "position": { "type": "string", "enum": ["top_left", "top_right", "bottom_left", "bottom_right"] }
              }
            }
          }
        },
        "budget": {
          "type": "object",
          "description": "成本预算控制",
          "properties": {
            "max_total_cost_usd": { "type": "number", "minimum": 0 },
            "max_per_shot_cost_usd": { "type": "number", "minimum": 0 },
            "mode": { "type": "string", "enum": ["observe", "warn", "cap"], "default": "warn" }
          }
        }
      }
    },

    "execution_scope": {
      "type": "object",
      "description": "执行范围——支持部分生成",
      "properties": {
        "episode_indices": { "type": "array", "items": { "type": "integer" } },
        "scene_ids": { "type": "array", "items": { "type": "string" } },
        "shot_ids": { "type": "array", "items": { "type": "string" } },
        "skip_stages": {
          "type": "array",
          "items": { "type": "string", "enum": ["image", "video", "tts", "composite"] },
          "description": "跳过的步骤（用于部分重做）"
        }
      }
    }
  }
}
```

### Output Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/stage4-production-output.json",
  "title": "ProductionOutput",
  "description": "制作阶段的输出——生成资产清单 + 合成视频 + 成本报告",

  "type": "object",
  "required": ["production_id", "project_id", "version", "generated_assets", "final_videos", "cost_report"],

  "properties": {
    "production_id": { "type": "string" },
    "project_id": { "type": "string" },
    "storyboard_id": { "type": "string" },
    "asset_set_id": { "type": "string" },
    "version": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "completed_at": { "type": "string", "format": "date-time" },
    "total_duration_seconds": { "type": "number" },

    "generated_assets": {
      "type": "object",
      "description": "按镜头索引的生成资产",
      "properties": {
        "by_shot_id": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "shot_id": { "type": "string" },
              "keyframe_image": {
                "type": "object",
                "properties": {
                  "url": { "type": "string", "format": "uri" },
                  "local_path": { "type": "string" },
                  "resolution": { "type": "string" },
                  "file_size_bytes": { "type": "integer" },
                  "generation_metadata": {
                    "type": "object",
                    "properties": {
                      "provider": { "type": "string" },
                      "model": { "type": "string" },
                      "seed": { "type": "integer" },
                      "actual_prompt": { "type": "string" },
                      "generation_time_ms": { "type": "integer" },
                      "cost_usd": { "type": "number" }
                    }
                  }
                }
              },
              "video_segment": {
                "type": "object",
                "properties": {
                  "url": { "type": "string", "format": "uri" },
                  "local_path": { "type": "string" },
                  "duration_ms": { "type": "integer" },
                  "resolution": { "type": "string" },
                  "fps": { "type": "integer" },
                  "file_size_bytes": { "type": "integer" },
                  "generation_metadata": {
                    "type": "object",
                    "properties": {
                      "provider": { "type": "string" },
                      "model": { "type": "string" },
                      "generation_time_ms": { "type": "integer" },
                      "cost_usd": { "type": "number" }
                    }
                  }
                }
              },
              "audio_segment": {
                "type": "object",
                "properties": {
                  "url": { "type": "string", "format": "uri" },
                  "local_path": { "type": "string" },
                  "dialogue_url": { "type": "string", "format": "uri", "description": "TTS 生成的对白音频" },
                  "duration_ms": { "type": "integer" },
                  "character_id": { "type": "string" },
                  "text": { "type": "string" },
                  "generation_metadata": {
                    "type": "object",
                    "properties": {
                      "provider": { "type": "string" },
                      "model": { "type": "string" },
                      "voice_id": { "type": "string" },
                      "cost_usd": { "type": "number" }
                    }
                  }
                }
              },
              "status": {
                "type": "string",
                "enum": ["pending", "image_generating", "image_done", "video_generating", "video_done", "audio_generating", "audio_done", "complete", "failed", "skipped"]
              },
              "error": {
                "type": "object",
                "properties": {
                  "stage": { "type": "string" },
                  "message": { "type": "string" },
                  "retry_count": { "type": "integer" },
                  "fatal": { "type": "boolean" }
                }
              }
            }
          }
        }
      }
    },

    "final_videos": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["episode_index", "output_url", "format"],
        "properties": {
          "episode_index": { "type": "integer" },
          "title": { "type": "string" },
          "output_url": { "type": "string", "format": "uri" },
          "local_path": { "type": "string" },
          "format": { "type": "string" },
          "codec": { "type": "string" },
          "resolution": { "type": "string" },
          "fps": { "type": "integer" },
          "duration_ms": { "type": "integer" },
          "file_size_bytes": { "type": "integer" },
          "has_subtitles": { "type": "boolean" },
          "subtitles_file": { "type": "string", "description": "SRT/VTT 字幕文件路径" },
          "thumbnail_url": { "type": "string", "format": "uri" },
          "checksum_md5": { "type": "string" }
        }
      }
    },

    "task_log": {
      "type": "array",
      "description": "任务执行日志",
      "items": {
        "type": "object",
        "properties": {
          "task_id": { "type": "string" },
          "shot_id": { "type": "string" },
          "type": { "type": "string", "enum": ["image_gen", "video_gen", "tts_gen", "composite"] },
          "status": { "type": "string", "enum": ["queued", "running", "succeeded", "failed", "cancelled"] },
          "started_at": { "type": "string", "format": "date-time" },
          "ended_at": { "type": "string", "format": "date-time" },
          "duration_ms": { "type": "integer" },
          "provider": { "type": "string" },
          "model": { "type": "string" },
          "cost_usd": { "type": "number" },
          "error_message": { "type": "string" }
        }
      }
    },

    "cost_report": {
      "type": "object",
      "required": ["total_cost_usd", "breakdown", "budget_compliance"],
      "properties": {
        "total_cost_usd": { "type": "number" },
        "breakdown": {
          "type": "object",
          "properties": {
            "image_generation_cost_usd": { "type": "number" },
            "video_generation_cost_usd": { "type": "number" },
            "tts_generation_cost_usd": { "type": "number" },
            "compositing_cost_usd": { "type": "number" }
          }
        },
        "by_provider": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "provider": { "type": "string" },
              "total_cost_usd": { "type": "number" },
              "call_count": { "type": "integer" },
              "average_latency_ms": { "type": "integer" }
            }
          }
        },
        "budget_compliance": {
          "type": "string",
          "enum": ["under_budget", "near_limit", "exceeded_warn", "exceeded_capped"],
          "description": "预算合规状态"
        }
      }
    },

    "quality_report": {
      "type": "object",
      "description": "自动质量检测结果",
      "properties": {
        "overall_score": { "type": "number", "minimum": 0, "maximum": 100 },
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "check_name": { "type": "string" },
              "passed": { "type": "boolean" },
              "score": { "type": "number" },
              "details": { "type": "string" }
            }
          }
        },
        "issues": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "shot_id": { "type": "string" },
              "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] },
              "type": { "type": "string", "enum": ["character_inconsistency", "scene_inconsistency", "artifact", "audio_sync", "subtitle_error", "missing_asset"] },
              "description": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

---

## 跨阶段元数据 (Cross-Stage Metadata)

每个阶段产出物共同携带的轻量元数据，用于项目仪表盘和进度追踪。

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-comic-studio/schemas/project-metadata.json",
  "title": "ProjectMetadata",
  "description": "跨阶段项目元数据——轻量汇总，不包含完整内容",

  "type": "object",
  "required": ["project_id", "title", "stages", "created_at", "updated_at"],

  "properties": {
    "project_id": { "type": "string" },
    "title": { "type": "string" },

    "stages": {
      "type": "object",
      "properties": {
        "script": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["not_started", "in_progress", "review", "locked", "revision"] },
            "script_id": { "type": "string" },
            "version": { "type": "integer" },
            "episode_count": { "type": "integer" },
            "scene_count": { "type": "integer" },
            "character_count": { "type": "integer" },
            "last_updated": { "type": "string", "format": "date-time" }
          }
        },
        "assets": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["not_started", "in_progress", "review", "locked", "revision"] },
            "asset_set_id": { "type": "string" },
            "version": { "type": "integer" },
            "character_count": { "type": "integer" },
            "location_count": { "type": "integer" },
            "prop_count": { "type": "integer" },
            "reference_images_generated": { "type": "integer" },
            "last_updated": { "type": "string", "format": "date-time" }
          }
        },
        "storyboard": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["not_started", "in_progress", "review", "locked", "revision"] },
            "storyboard_id": { "type": "string" },
            "version": { "type": "integer" },
            "total_shots": { "type": "integer" },
            "total_duration_ms": { "type": "integer" },
            "last_updated": { "type": "string", "format": "date-time" }
          }
        },
        "production": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["not_started", "in_progress", "partial_complete", "complete", "failed"] },
            "production_id": { "type": "string" },
            "version": { "type": "integer" },
            "shots_completed": { "type": "integer" },
            "shots_total": { "type": "integer" },
            "videos_exported": { "type": "integer" },
            "total_cost_usd": { "type": "number" },
            "last_updated": { "type": "string", "format": "date-time" }
          }
        }
      }
    },

    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "completed_at": { "type": "string", "format": "date-time" },

    "current_stage": {
      "type": "string",
      "enum": ["script", "assets", "storyboard", "production", "complete"],
      "description": "项目当前所处阶段"
    }
  }
}
```

---

## 数据流转总结

```
  Stage 0                  Stage 1                  Stage 2                  Stage 3                  Stage 4
┌────────────┐         ┌────────────┐           ┌────────────┐           ┌────────────┐           ┌────────────┐
│ProjectInput│ ──────→ │  Script    │ ────────→ │  Assets    │ ────────→ │ Storyboard │ ────────→ │ Production │
│            │         │            │           │            │           │            │           │            │
│·source     │         │·episodes[] │           │·characters │           │·episodes[] │           │·videos[]   │
│·genre      │         │·scenes[]  │           │·locations  │           │·shots[]    │           │·task_log   │
│·target_spec│         │·character │           │·props[]    │           │·keyframes  │           │·cost_report│
│·style      │         │  _index   │           │·style_     │           │·dialogue   │           │            │
└────┬───────┘         │·location  │           │  manifest  │           │  _mapping  │           └────────────┘
     │                 │  _index   │           └─────┬──────┘           └─────┬──────┘
     │                 └─────┬──────┘                 │                       │
     │                       │                       │                       │
     ▼                       ▼                       ▼                       ▼
  creative_input.json   structured_script.json   asset_profiles.json    shot_plan.json
                                                                              │
                                                          ┌───────────────────┘
                                                          ▼
                                                    final_video.mp4
```

### 关键设计决策

| 决策 | 理由 |
|------|------|
| **Stage 1-3 用 Multi-Agent，Stage 4 用 Pipeline** | 创意阶段需要多角度审视；制作阶段需要确定性执行 |
| **每个 Stage Output 携带 `review_history`** | 可追溯 Agent 决策过程，支持撤销和审计 |
| **`status` 字段支持 `locked` 状态** | 防止下游阶段启动后上游数据被意外修改 |
| **Seed 体系贯穿 Stage 2→4** | 全局种子→角色种子→镜头种子，保证视觉一致性可复现 |
| **Stage 4 支持 `execution_scope`** | 允许部分重做，不浪费已完成的计算 |
| **Cost 追踪从 Stage 4 内建** | 参考 Open Montage 的 Budget Governance 设计 |
| **所有 ID 使用结构化前缀** | `CHAR-0001`, `SH-E001-S003-005` 可实现正则快速查找 |
