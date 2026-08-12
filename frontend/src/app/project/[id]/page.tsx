import { useParams, useNavigate } from "react-router-dom";
import { FileText, Image, LayoutGrid, Film, ChevronRight, CheckCircle, ArrowRight } from "lucide-react";

const stages = [
  { key: "script", label: "剧本创作", desc: "编写和审查剧本", icon: FileText, color: "var(--color-stage-script)" },
  { key: "assets", label: "资产设计", desc: "角色、场景、道具", icon: Image, color: "var(--color-stage-assets)" },
  { key: "storyboard", label: "分镜设计", desc: "镜头拆解和构图", icon: LayoutGrid, color: "var(--color-stage-storyboard)" },
  { key: "production", label: "制作合成", desc: "AI 生成和视频合成", icon: Film, color: "var(--color-stage-production)" },
];

export function ProjectDashboard() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold">项目概览</h1>
          <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-surface-2 text-muted-foreground">{id}</span>
        </div>
        <p className="text-muted-foreground">AI 漫剧全自动创作 — 四阶段管线进度总览</p>
      </div>

      {/* Pipeline steps */}
      <div className="mb-8 p-6 rounded-xl bg-surface-1 border border-border">
        <div className="flex items-center justify-between">
          {stages.map((s, i) => (
            <div key={s.key} className="flex items-center gap-0 flex-1">
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center border-2 transition-all"
                  style={{ borderColor: s.color, backgroundColor: `${s.color}10` }}>
                  <s.icon className="w-6 h-6" style={{ color: s.color }} />
                </div>
                <span className="text-xs font-medium">{s.label}</span>
                <span className="text-[10px] text-muted-foreground font-mono">S{i+1}</span>
              </div>
              {i < stages.length - 1 && (
                <div className="flex-1 mx-2 h-px" style={{ backgroundColor: "var(--color-border)" }}>
                  <ArrowRight className="w-4 h-4 text-muted-foreground hidden" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stage detail cards */}
      <div className="grid grid-cols-2 gap-4">
        {stages.map((s) => (
          <button key={s.key} onClick={() => navigate(`/project/${id}/${s.key}`)}
            className="flex items-start gap-4 p-5 rounded-xl bg-surface-1 border border-border text-left hover:border-[var(--color-border-hover)] hover:bg-surface-2 transition-all group">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${s.color}15` }}>
              <s.icon className="w-6 h-6" style={{ color: s.color }} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm">{s.label}</h3>
              <p className="text-xs text-muted-foreground mt-1">{s.desc}</p>
              <div className="flex items-center gap-2 mt-3">
                <span className="flex items-center gap-1 text-[10px] text-success">
                  <CheckCircle className="w-3 h-3" /> 可执行
                </span>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors mt-3" />
          </button>
        ))}
      </div>
    </div>
  );
}
