import { useNavigate } from "react-router-dom";
import { Plus, Clapperboard, Play, FileText, Image, LayoutGrid, Film, ChevronRight } from "lucide-react";

const demoProjects = [
  { id: "PRJ-0001", title: "觉醒之夜", stage: "storyboard", genre: "urban", updated: "2026-08-12", progress: 75 },
  { id: "PRJ-0002", title: "仙道长生", stage: "script", genre: "xianxia", updated: "2026-08-10", progress: 25 },
  { id: "PRJ-0003", title: "赛博江湖", stage: "complete", genre: "sci_fi", updated: "2026-08-08", progress: 100 },
];

const stageColors: Record<string, string> = {
  script: "var(--color-stage-script)",
  assets: "var(--color-stage-assets)",
  storyboard: "var(--color-stage-storyboard)",
  production: "var(--color-stage-production)",
  complete: "var(--color-success)",
};
const stageLabels: Record<string, string> = {
  script: "剧本", assets: "资产", storyboard: "分镜", production: "制作", complete: "已完成",
};
const stageIcons: Record<string, any> = {
  script: FileText, assets: Image, storyboard: LayoutGrid, production: Film, complete: Film,
};

export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI 漫剧创作平台</h1>
          <p className="text-muted-foreground mt-1">从剧本到成片 — 一站式 AI 漫剧全自动创作管线</p>
        </div>
        <button
          onClick={() => navigate("/project/new")}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary-hover transition-all shadow-lg shadow-primary/20"
        >
          <Plus className="w-4 h-4" /> 新建项目
        </button>
      </div>

      {/* Project list */}
      {demoProjects.length > 0 ? (
        <div className="space-y-3">
          {demoProjects.map((p) => {
            const Icon = stageIcons[p.stage] || FileText;
            const color = stageColors[p.stage] || "var(--color-muted-foreground)";
            return (
              <button
                key={p.id}
                onClick={() => navigate(`/project/${p.id}`)}
                className="w-full flex items-center gap-5 p-5 rounded-xl bg-surface-1 border border-border hover:border-[var(--color-border-hover)] hover:bg-surface-2 transition-all text-left group"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                  style={{ backgroundColor: `${color}15` }}>
                  <Icon className="w-6 h-6" style={{ color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{p.title}</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-2 text-muted-foreground">{p.genre}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }}/>
                      <span className="text-xs text-muted-foreground">{stageLabels[p.stage]}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{p.updated}</span>
                    <span className="text-xs font-mono text-muted-foreground">{p.id}</span>
                  </div>
                </div>
                {/* Progress */}
                <div className="shrink-0 flex items-center gap-3">
                  <div className="w-24">
                    <div className="h-1.5 rounded-full bg-surface-3 overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${p.progress}%`, backgroundColor: color }}/>
                    </div>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground w-8 text-right">{p.progress}%</span>
                  <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="border border-border rounded-xl p-16 text-center bg-surface-1">
          <Clapperboard className="w-20 h-20 mx-auto mb-4 text-muted-foreground opacity-30" />
          <h2 className="text-lg font-semibold mb-2">还没有项目</h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">创建你的第一个 AI 漫剧项目，从剧本到成片，全自动管线一气呵成</p>
          <button onClick={() => navigate("/project/new")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary-hover transition-all">
            <Play className="w-4 h-4" /> 开始创作
          </button>
        </div>
      )}

      {/* Quick stats */}
      <div className="mt-8 grid grid-cols-4 gap-4">
        {[
          { label: "剧本生成", icon: FileText, color: "var(--color-stage-script)" },
          { label: "资产设计", icon: Image, color: "var(--color-stage-assets)" },
          { label: "分镜编排", icon: LayoutGrid, color: "var(--color-stage-storyboard)" },
          { label: "视频合成", icon: Film, color: "var(--color-stage-production)" },
        ].map((s, i) => (
          <div key={i} className="p-4 rounded-xl bg-surface-1 border border-border">
            <s.icon className="w-5 h-5 mb-2" style={{ color: s.color }}/>
            <p className="text-xs text-muted-foreground">Stage {i+1}</p>
            <p className="text-sm font-semibold mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
