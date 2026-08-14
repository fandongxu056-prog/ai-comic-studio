import { useParams } from "react-router-dom";
import {
  Film, Pause, CheckCircle, Loader2, AlertTriangle, Clock,
  Image, Video, Music, Clapperboard, DollarSign, Download,
  BarChart3, Eye,
} from "lucide-react";
import { api } from "@/services/api";
import { useStageData } from "@/hooks/use-stage-data";
import { mockProduction } from "@/stores/mock-data";

const SC = "var(--color-stage-production)";

const statusIcons: Record<string, any> = {
  complete: CheckCircle, image_done: CheckCircle, video_generating: Loader2,
  image_generating: Loader2, pending: Clock, failed: AlertTriangle,
};
const statusColors: Record<string, string> = {
  complete: "text-success", image_done: "text-info", video_generating: "text-warning",
  image_generating: "text-warning", pending: "text-muted-foreground", failed: "text-destructive",
};

export function ProductionWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { data: prod } = useStageData<typeof mockProduction>({
    mock: mockProduction,
    fetch: async () => {
      if (!id) return mockProduction;
      const status = await api.get<any>(`/productions/${id}/status`);
      return (status.production_id ? { ...mockProduction, ...status } : mockProduction) as typeof mockProduction;
    },
    hasData: (d) => (d as any).production_id !== "PRD-0001" && (d as any).status !== "not_started",
  });

  const byShot: Record<string, any> = prod.generated_assets.by_shot_id;
  const shots = Object.entries(byShot);
  const completed = shots.filter(([_,s]) => s.status === "complete").length;
  const progress = prod.shots_total > 0 ? (completed / prod.shots_total) * 100 : 0;

  const phases = [
    { key: "image", label: "图片生成", icon: Image, done: shots.filter(([_,s])=>s.keyframe_image).length, total: prod.shots_total },
    { key: "video", label: "视频生成", icon: Video, done: shots.filter(([_,s])=>s.video_segment).length, total: prod.shots_total },
    { key: "audio", label: "配音合成", icon: Music, done: 0, total: 0 },
    { key: "composite", label: "剪辑合成", icon: Clapperboard, done: prod.videos_exported, total: prod.shots_total > 0 ? 1 : 0 },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-border bg-surface-1 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center animate-pulse-glow" style={{ backgroundColor: "rgba(16,185,129,0.2)" }}>
              <Film className="w-5 h-5" style={{ color: SC }} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">制作合成</h1>
              <p className="text-xs text-muted-foreground">Stage 4 · Pipeline 执行中 · ${prod.total_cost_usd.toFixed(2)} 已消耗</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {prod.status !== "complete" && (
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2"><Pause className="w-4 h-4"/>暂停</button>
            )}
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90" style={{ backgroundColor: SC }}>
              <Download className="w-4 h-4"/>导出
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Progress overview */}
          <div className="shrink-0 px-6 py-4 border-b border-border/50 space-y-3">
            {/* Big progress bar */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-medium">总进度</span>
                <span className="text-sm font-mono font-semibold" style={{ color: SC }}>{completed}/{prod.shots_total} 镜头 ({progress.toFixed(0)}%)</span>
              </div>
              <div className="h-2 rounded-full bg-surface-2 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-1000 ease-out" style={{
                  width: `${progress}%`, backgroundColor: SC,
                  boxShadow: "0 0 12px rgba(16,185,129,0.4)",
                }}/>
              </div>
            </div>
            {/* Phase indicators */}
            <div className="grid grid-cols-4 gap-3">
              {phases.map(p => (
                <div key={p.key} className={`p-3 rounded-xl border transition-all ${
                  p.done > 0 ? "border-[var(--color-stage-production)]/30 bg-[var(--color-stage-production)]/5" : "border-border bg-surface-2"
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <p.icon className={`w-4 h-4 ${p.done > 0 ? "" : "text-muted-foreground"}`} style={p.done > 0 ? { color: SC } : {}}/>
                    <span className="text-xs font-medium">{p.label}</span>
                  </div>
                  <p className="text-lg font-bold font-mono" style={p.done > 0 ? { color: SC } : {}}>
                    {p.done}<span className="text-xs text-muted-foreground font-normal">/{p.total}</span>
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Shot status grid */}
          <div className="flex-1 overflow-y-auto p-6">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Eye className="w-4 h-4 text-muted-foreground"/>镜头状态</h3>
            <div className="grid grid-cols-3 gap-3">
              {shots.map(([shotId, shot]) => {
                const StatusIcon = statusIcons[shot.status] || Clock;
                const colorClass = statusColors[shot.status] || "text-muted-foreground";
                return (
                  <div key={shotId} className="p-3 rounded-xl border border-border bg-surface-1 hover:border-[var(--color-stage-production)]/30 transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono text-muted-foreground">{shotId}</span>
                      <StatusIcon className={`w-4 h-4 ${colorClass} ${shot.status === "video_generating" ? "animate-spin" : ""}`}
                        style={shot.status === "video_generating" ? { animationDuration: "3s" } : {}}/>
                    </div>
                    <div className="flex items-center gap-2">
                      {shot.keyframe_image ? (
                        <span className="flex items-center gap-1 text-[10px] text-info"><Image className="w-3 h-3"/>已生成</span>
                      ) : <span className="text-[10px] text-muted-foreground">图片待生成</span>}
                      {shot.video_segment ? (
                        <span className="flex items-center gap-1 text-[10px] text-success"><Video className="w-3 h-3"/>已生成({shot.video_segment.duration_ms/1000}s)</span>
                      ) : shot.keyframe_image ? (
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground">视频待生成</span>
                      ) : null}
                    </div>
                    <div className="mt-2 h-1 rounded-full bg-surface-2 overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{
                        width: shot.status === "complete" ? "100%" : shot.status === "video_generating" ? "60%" : shot.keyframe_image ? "40%" : "10%",
                        backgroundColor: shot.status === "complete" ? SC : shot.status === "failed" ? "var(--color-destructive)" : "var(--color-warning)",
                      }}/>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Cost + Log */}
        <div className="w-72 shrink-0 border-l border-border bg-surface-1 overflow-y-auto p-4 space-y-4">
          {/* Cost report */}
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-2"><DollarSign className="w-4 h-4 text-muted-foreground"/>成本报告</h3>
            <div className="p-3 rounded-lg bg-surface-2 border border-border">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">总消耗</span>
                <span className="text-lg font-bold font-mono" style={{ color: SC }}>${prod.total_cost_usd.toFixed(2)}</span>
              </div>
              <div className="space-y-1.5">
                {Object.entries(prod.cost_report.breakdown).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono">${(val as number).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
                <span className="text-xs text-muted-foreground">预算合规</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-success/10 text-success font-medium">
                  {prod.cost_report.budget_compliance === "under_budget" ? "预算内" : "超预算"}
                </span>
              </div>
            </div>
          </div>

          {/* Task log */}
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-muted-foreground"/>任务日志</h3>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {prod.task_log.map((t, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs hover:bg-surface-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${t.status === "succeeded" ? "bg-success" : t.status === "running" ? "bg-warning animate-pulse" : "bg-destructive"}`}/>
                  <span className="text-muted-foreground font-mono w-20 truncate">{t.shot_id}</span>
                  <span className="text-muted-foreground">{t.type === "image_gen" ? "图片" : t.type === "video_gen" ? "视频" : t.type}</span>
                  <span className="ml-auto text-muted-foreground font-mono">${t.cost_usd.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Output preview placeholder */}
          <div>
            <h3 className="text-sm font-semibold mb-2">成品预览</h3>
            <div className="aspect-video rounded-xl bg-surface-2 border border-border flex flex-col items-center justify-center gap-2 overflow-hidden">
              <Film className="w-8 h-8 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">制作完成后可预览</p>
              {progress > 50 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/10 text-success">即将完成...</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
