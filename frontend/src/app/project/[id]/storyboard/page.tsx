import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  LayoutGrid, Play, Camera, Clock, ChevronDown, ChevronUp,
  CheckCircle, ThumbsUp, ThumbsDown, RefreshCw, MessageSquare,
} from "lucide-react";
import { api } from "@/services/api";
import { useStageData } from "@/hooks/use-stage-data";
import { mockStoryboard } from "@/stores/mock-data";

const SC = "var(--color-stage-storyboard)";

const shotTypeLabels: Record<string, string> = {
  long_shot: "远景", full_shot: "全景", medium_shot: "中景", close_up: "特写",
  extreme_close_up: "大特写", medium_close_up: "近景", over_shoulder: "过肩", pov: "POV", dutch_angle: "斜角",
};
const angleLabels: Record<string, string> = {
  eye_level: "平视", low_angle: "仰角", high_angle: "俯角", dutch: "倾斜",
};

export function StoryboardWorkspace() {
  const { id } = useParams<{ id: string }>();
  const [epIdx, setEpIdx] = useState(0);
  const [expandedScene, setExpandedScene] = useState<number | null>(0);
  const [selectedShot, setSelectedShot] = useState<string | null>(null);

  const { data: storyboard } = useStageData<typeof mockStoryboard>({
    mock: mockStoryboard,
    fetch: async () => {
      if (!id) return mockStoryboard;
      const shots = await api.get<any>(`/storyboards/${id}/shots?episode=1`);
      const epShots = shots.shots?.length ? shots.shots : null;
      return epShots
        ? { ...mockStoryboard, episodes: [{ ...mockStoryboard.episodes[0], scenes: epShots }] as typeof mockStoryboard.episodes }
        : mockStoryboard;
    },
    hasData: (d) => d.episodes.length > 0,
  });
  const ep = storyboard.episodes[epIdx];
  if (!ep) return null;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-border bg-surface-1 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(249,115,22,0.15)" }}>
              <LayoutGrid className="w-5 h-5" style={{ color: SC }} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">分镜设计</h1>
              <p className="text-xs text-muted-foreground">Stage 3 · {storyboard.total_shots}镜头 · {(storyboard.total_duration_ms/1000).toFixed(0)}秒总长</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2"><RefreshCw className="w-4 h-4"/>重新生成</button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90" style={{ backgroundColor: SC }}><Play className="w-4 h-4"/>继续分镜</button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Main: Shot timeline */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Episode tabs */}
          <div className="shrink-0 px-6 pt-4 pb-3 flex items-center gap-2 border-b border-border/50">
            {storyboard.episodes.map((e, i) => (
              <button key={i} onClick={() => { setEpIdx(i); setExpandedScene(0); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  i === epIdx ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                }`}
                style={i === epIdx ? { backgroundColor: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)" } : {}}
              >
                第{e.episode_index}集<span className="block text-[10px] text-muted-foreground font-normal">{e.scenes.length}场</span>
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {ep.scenes.map((scene, si) => (
              <div key={scene.scene_id} className="rounded-xl border border-border bg-surface-1 overflow-hidden">
                {/* Scene header */}
                <button onClick={() => setExpandedScene(expandedScene === si ? null : si)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-2 transition-colors">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono font-bold"
                    style={{ backgroundColor: "rgba(249,115,22,0.15)", color: SC }}>{si + 1}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">场景 {scene.scene_id}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-muted-foreground">{scene.scene_mood}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{scene.shots.length} 个镜头</p>
                  </div>
                  {expandedScene === si ? <ChevronUp className="w-4 h-4 text-muted-foreground"/> : <ChevronDown className="w-4 h-4 text-muted-foreground"/>}
                </button>

                {expandedScene === si && (
                  <div className="border-t border-border animate-fade-in">
                    {/* Shot cards */}
                    <div className="divide-y divide-border/30">
                      {scene.shots.map((shot) => (
                        <div key={shot.shot_id}
                          className={`p-4 hover:bg-surface-2/50 transition-colors cursor-pointer ${
                            selectedShot === shot.shot_id ? "bg-surface-2 border-l-2" : ""
                          }`}
                          style={selectedShot === shot.shot_id ? { borderLeftColor: SC, borderLeftWidth: "3px" } : {}}
                          onClick={() => setSelectedShot(selectedShot === shot.shot_id ? null : shot.shot_id)}
                        >
                          <div className="flex items-start gap-4">
                            {/* Shot thumbnail placeholder */}
                            <div className="w-24 h-14 shrink-0 rounded-lg bg-surface-2 border border-border flex items-center justify-center overflow-hidden">
                              <Camera className="w-6 h-6 text-muted-foreground" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-mono font-semibold text-muted-foreground">{shot.shot_id}</span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 font-medium">
                                  {shotTypeLabels[shot.shot_type] || shot.shot_type}
                                </span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                                  {angleLabels[shot.camera_angle] || shot.camera_angle}
                                </span>
                                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                                  <Clock className="w-3 h-3"/>{(shot.duration_ms/1000).toFixed(1)}s
                                </span>
                              </div>
                              {/* Prompt preview */}
                              <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">
                                {shot.keyframe.image_prompt.positive.slice(0, 120)}...
                              </p>
                              {/* Dialogue */}
                              {shot.dialogue.length > 0 && (
                                <div className="flex items-center gap-1 mt-1.5">
                                  <MessageSquare className="w-3 h-3 text-purple-400"/>
                                  {shot.dialogue.map((d,i) => (
                                    <span key={i} className="text-[10px] text-purple-400">"{d.text.slice(0,30)}..."</span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="shrink-0 flex flex-col items-end gap-1">
                              <span className="text-[10px] text-muted-foreground font-mono">Seed: {shot.keyframe.image_prompt.seed}</span>
                            </div>
                          </div>

                          {/* Expanded shot detail */}
                          {selectedShot === shot.shot_id && (
                            <div className="mt-3 pt-3 border-t border-border animate-fade-in space-y-3">
                              <div className="grid grid-cols-2 gap-2">
                                <div className="p-2 rounded-lg bg-surface-3">
                                  <span className="text-[10px] text-muted-foreground">构图焦点</span>
                                  <p className="text-xs mt-0.5">{shot.keyframe.composition.subject_focus}</p>
                                </div>
                                <div className="p-2 rounded-lg bg-surface-3">
                                  <span className="text-[10px] text-muted-foreground">景深</span>
                                  <p className="text-xs mt-0.5">{(shot.keyframe.composition as any).depth_of_field || "medium"}</p>
                                </div>
                              </div>
                              <div>
                                <span className="text-[10px] text-muted-foreground">正向提示词</span>
                                <div className="mt-1 p-2 rounded-lg bg-surface-3">
                                  <code className="text-xs text-muted-foreground break-all">{shot.keyframe.image_prompt.positive.slice(0, 300)}</code>
                                </div>
                              </div>
                              {shot.keyframe.image_prompt.negative && (
                                <div>
                                  <span className="text-[10px] text-destructive">负向提示词</span>
                                  <div className="mt-1 p-2 rounded-lg bg-surface-3"><code className="text-xs text-muted-foreground">{shot.keyframe.image_prompt.negative}</code></div>
                                </div>
                              )}
                              {shot.dialogue.length > 0 && (
                                <div>
                                  <span className="text-[10px] text-muted-foreground">对白时间线</span>
                                  {shot.dialogue.map((d,i) => (
                                    <div key={i} className="mt-1 p-2 rounded-lg bg-surface-3 flex items-center gap-2">
                                      <span className="text-[10px] font-mono text-muted-foreground">{d.start_ms}ms-{d.end_ms}ms</span>
                                      <span className="text-xs font-semibold text-purple-400">{d.character_id}</span>
                                      <span className="text-xs">{d.text}</span>
                                      <span className="text-[10px] text-muted-foreground">[{d.emotion}]</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Pacing + Review */}
        <div className="w-72 shrink-0 border-l border-border bg-surface-1 overflow-y-auto p-4 space-y-4">
          {/* Pacing analysis */}
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-2"><Clock className="w-4 h-4 text-muted-foreground"/>节奏分析</h3>
            <div className="p-3 rounded-lg bg-surface-2 border border-border">
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div><span className="text-muted-foreground">短镜头</span><p className="font-semibold">{storyboard.tempo_analysis.shot_duration_distribution.short_count}</p></div>
                <div><span className="text-muted-foreground">中镜头</span><p className="font-semibold">{storyboard.tempo_analysis.shot_duration_distribution.medium_count}</p></div>
                <div><span className="text-muted-foreground">长镜头</span><p className="font-semibold">{storyboard.tempo_analysis.shot_duration_distribution.long_count}</p></div>
              </div>
            </div>
            {/* Tension curve */}
            <div className="mt-3 p-3 rounded-lg bg-surface-2 border border-border">
              <span className="text-xs text-muted-foreground">张力曲线</span>
              <div className="flex items-end gap-1 mt-2 h-16">
                {storyboard.tempo_analysis.pacing_curve.map((p,i) => (
                  <div key={i} className="flex-1 rounded-t" style={{
                    height: `${p.tension_level * 10}%`,
                    backgroundColor: p.tension_level > 7 ? "var(--color-destructive)" :
                                    p.tension_level > 4 ? "var(--color-warning)" : "var(--color-info)",
                    opacity: 0.7,
                  }} title={`镜头${i+1}: 张力${p.tension_level}`}/>
                ))}
              </div>
            </div>
          </div>

          {/* Review */}
          <div>
            <h3 className="text-sm font-semibold mb-2">审查结果</h3>
            {storyboard.review_history.map((r,i) => (
              <div key={i} className="p-3 rounded-lg bg-surface-2 border border-border">
                <div className="flex items-center justify-between"><span className="text-xs font-semibold">Round {r.round}</span><span className="text-xs text-success font-medium flex items-center gap-1"><CheckCircle className="w-3 h-3"/>{r.total_score}分</span></div>
              </div>
            ))}
            <div className="flex gap-2 mt-3">
              <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-success/10 border border-success/30 text-success text-sm font-medium hover:bg-success/20"><ThumbsUp className="w-4 h-4"/>通过</button>
              <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm font-medium hover:bg-destructive/20"><ThumbsDown className="w-4 h-4"/>打回</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
