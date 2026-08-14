import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Image, User, Building2, Box, Palette, Sparkles,
  CheckCircle, AlertTriangle, ThumbsUp, ThumbsDown, RefreshCw, Eye,
} from "lucide-react";
import { api } from "@/services/api";
import { useStageData } from "@/hooks/use-stage-data";
import { mockAssets } from "@/stores/mock-data";

const SC = "var(--color-stage-assets)";

export function AssetWorkspace() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<"characters" | "locations" | "props" | "style">("characters");
  const [selectedChar, setSelectedChar] = useState(0);

  const { data: assets } = useStageData<typeof mockAssets>({
    mock: mockAssets,
    fetch: async () => {
      if (!id) return mockAssets;
      const [chars, locs] = await Promise.all([
        api.get<any>(`/assets/${id}/characters`),
        api.get<any>(`/assets/${id}/locations`),
      ]);
      return {
        ...mockAssets,
        characters: (chars.characters?.length ? chars.characters : mockAssets.characters) as typeof mockAssets.characters,
        locations: (locs.locations?.length ? locs.locations : mockAssets.locations) as typeof mockAssets.locations,
        style_manifest: (chars.style_manifest || mockAssets.style_manifest) as typeof mockAssets.style_manifest,
      };
    },
    hasData: (d) => d.characters.length > 0,
  });
  const character = assets.characters[selectedChar];

  const tabs = [
    { key: "characters" as const, label: "角色", icon: User, count: assets.characters.length },
    { key: "locations" as const, label: "场景", icon: Building2, count: assets.locations.length },
    { key: "props" as const, label: "道具", icon: Box, count: assets.props.length },
    { key: "style" as const, label: "风格", icon: Palette, count: 1 },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-border bg-surface-1 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(139,92,246,0.15)" }}>
              <Image className="w-5 h-5" style={{ color: SC }} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">资产设计</h1>
              <p className="text-xs text-muted-foreground">Stage 2 · {assets.characters.length}角色 · {assets.locations.length}场景 · {assets.props.length}道具</p>
            </div>
            <div className="flex items-center gap-2 ml-4 px-3 py-1.5 rounded-full bg-success/10 border border-success/30">
              <CheckCircle className="w-3.5 h-3.5 text-success" />
              <span className="text-sm font-semibold text-success">已通过</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2"><RefreshCw className="w-4 h-4"/>重新生成</button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90" style={{ backgroundColor: SC }}><Sparkles className="w-4 h-4"/>继续设计</button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Tab content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="shrink-0 px-6 pt-4 pb-3 flex items-center gap-2 border-b border-border/50">
            {tabs.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === t.key ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                }`}
                style={tab === t.key ? { backgroundColor: "rgba(139,92,246,0.12)", border: "1px solid rgba(139,92,246,0.3)" } : {}}
              >
                <t.icon className="w-4 h-4" style={{ color: tab === t.key ? SC : undefined }} />
                {t.label}<span className="text-[10px] text-muted-foreground">({t.count})</span>
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {/* Characters Tab */}
            {tab === "characters" && (
              <div className="flex gap-6 h-full">
                {/* Character list */}
                <div className="w-52 shrink-0 space-y-1">
                  {assets.characters.map((c, i) => (
                    <button key={c.character_id} onClick={() => setSelectedChar(i)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all ${
                        i === selectedChar ? "bg-surface-3 font-medium" : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                      }`}
                      style={i === selectedChar ? { borderLeft: `3px solid ${SC}` } : {}}
                    >
                      <div className="flex items-center justify-between">
                        {c.ref_name}
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                          c.role_type === "protagonist" ? "bg-amber-500/15 text-amber-400" : "bg-surface-3 text-muted-foreground"
                        }`}>
                          {c.role_type === "protagonist" ? "主角" : c.role_type === "supporting" ? "配角" : "客串"}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
                {/* Character detail */}
                {character && (
                  <div className="flex-1 space-y-6 animate-fade-in">
                    <div className="flex items-start gap-4">
                      <div className="w-24 h-24 rounded-xl bg-surface-2 border border-border flex items-center justify-center shrink-0">
                        <User className="w-10 h-10 text-muted-foreground" />
                      </div>
                      <div className="flex-1">
                        <h2 className="text-lg font-semibold">{character.ref_name}</h2>
                        <p className="text-sm text-muted-foreground">ID: {character.character_id}</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs px-2 py-1 rounded-lg bg-surface-2">{character.design_sheet.appearance.age_appearance} · {character.design_sheet.appearance.gender}</span>
                          <span className="text-xs px-2 py-1 rounded-lg bg-surface-2">{character.design_sheet.appearance.body_type}</span>
                          <span className="text-xs px-2 py-1 rounded-lg bg-surface-2">{character.design_sheet.appearance.face.shape} · {character.design_sheet.appearance.face.eyes}</span>
                        </div>
                      </div>
                    </div>
                    {/* Costumes */}
                    <div>
                      <h3 className="text-sm font-semibold mb-2">服装设计</h3>
                      <div className="space-y-2">
                        {character.design_sheet.costumes.map(cost => (
                          <div key={cost.costume_id} className="p-3 rounded-lg bg-surface-2 border border-border flex items-start gap-3">
                            <div className="w-10 h-10 rounded-lg bg-surface-3 flex items-center justify-center shrink-0"><Eye className="w-5 h-5 text-muted-foreground"/></div>
                            <div><p className="text-sm font-medium">{cost.name}</p><p className="text-xs text-muted-foreground">{cost.description}</p></div>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Expressions */}
                    <div>
                      <h3 className="text-sm font-semibold mb-2">关键表情</h3>
                      <div className="grid grid-cols-3 gap-2">
                        {Object.entries(character.design_sheet.expressions).map(([name, desc]) => (
                          <div key={name} className="p-3 rounded-lg bg-surface-2 border border-border text-center">
                            <span className="text-xs font-semibold text-muted-foreground">{name}</span>
                            <p className="text-xs mt-1">{desc}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Prompt template */}
                    <div>
                      <h3 className="text-sm font-semibold mb-2">生成提示词模板</h3>
                      <div className="p-3 rounded-lg bg-surface-2 border border-border">
                        <code className="text-xs text-muted-foreground break-all">{character.character_prompt_template}</code>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Locations Tab */}
            {tab === "locations" && (
              <div className="grid grid-cols-2 gap-4">
                {assets.locations.map(loc => (
                  <div key={loc.location_id} className="p-4 rounded-xl bg-surface-1 border border-border hover:border-[var(--color-stage-assets)]/30 transition-all">
                    <div className="w-full h-32 rounded-lg bg-surface-2 flex items-center justify-center mb-3">
                      <Building2 className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <h3 className="font-semibold text-sm">{loc.name}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{loc.design_sheet.description}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {loc.design_sheet.key_features.map((f,i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-muted-foreground">{f}</span>
                      ))}
                    </div>
                    <div className="mt-3 p-2 rounded-lg bg-surface-2">
                      <code className="text-[10px] text-muted-foreground break-all">{loc.location_prompt_template.slice(0, 80)}...</code>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Props Tab */}
            {tab === "props" && (
              <div className="space-y-3">
                {assets.props.map(prop => (
                  <div key={prop.prop_id} className="p-4 rounded-xl bg-surface-1 border border-border flex items-start gap-4 hover:border-[var(--color-stage-assets)]/30 transition-all">
                    <div className="w-12 h-12 rounded-lg bg-surface-2 flex items-center justify-center shrink-0"><Box className="w-6 h-6 text-muted-foreground"/></div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-sm">{prop.name}</h3>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                          prop.importance === "key_item" ? "bg-amber-500/15 text-amber-400" :
                          prop.importance === "recurring" ? "bg-blue-500/15 text-blue-400" : "bg-surface-3 text-muted-foreground"
                        }`}>
                          {prop.importance === "key_item" ? "关键道具" : prop.importance === "recurring" ? "常驻" : "单次"}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{prop.design.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Style Tab */}
            {tab === "style" && (
              <div className="max-w-2xl space-y-6">
                <div className="p-4 rounded-xl bg-surface-1 border border-border">
                  <h3 className="text-sm font-semibold mb-3">风格清单</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="p-3 rounded-lg bg-surface-2"><span className="text-muted-foreground">美术风格</span><p className="font-medium mt-1">{assets.style_manifest.art_style}</p></div>
                    <div className="p-3 rounded-lg bg-surface-2"><span className="text-muted-foreground">全局种子</span><p className="font-medium mt-1 font-mono">{assets.style_manifest.global_style_seed}</p></div>
                  </div>
                  <div className="mt-3">
                    <span className="text-xs text-muted-foreground">色板</span>
                    <div className="flex gap-2 mt-1">
                      {assets.style_manifest.color_palette.primary_colors.map((c,i) => (
                        <div key={i} className="w-8 h-8 rounded-lg border border-border" style={{ backgroundColor: c }} title={c} />
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-success/10 border border-success/30 text-success text-sm font-medium hover:bg-success/20"><ThumbsUp className="w-4 h-4"/>通过</button>
                  <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm font-medium hover:bg-destructive/20"><ThumbsDown className="w-4 h-4"/>打回</button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Review */}
        <div className="w-72 shrink-0 border-l border-border bg-surface-1 p-4 overflow-y-auto">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-warning"/>审查结果</h3>
          {assets.review_history.map((r,i) => (
            <div key={i} className="p-3 rounded-lg bg-surface-2 border border-border mb-2">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold">一致性审查</span><span className="text-xs text-success font-medium flex items-center gap-1"><CheckCircle className="w-3 h-3"/>{r.total_score}分</span></div>
              <p className="text-xs text-muted-foreground mt-1">所有资产风格统一、比例协调</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
