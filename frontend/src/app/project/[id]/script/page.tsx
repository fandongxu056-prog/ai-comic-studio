import { useState } from "react";
import {
  FileText, Users, MapPin, CheckCircle, AlertTriangle,
  ChevronDown, ChevronUp, MessageSquare, Zap, Eye,
  ThumbsUp, ThumbsDown, RefreshCw,
} from "lucide-react";
import { mockScript } from "@/stores/mock-data";

const SC = "var(--color-stage-script)";

export function ScriptWorkspace() {
  const [epIdx, setEpIdx] = useState(0);
  const [expanded, setExpanded] = useState<number | null>(0);
  const [showReview, setShowReview] = useState(true);

  const script = mockScript;
  const ep = script.episodes[epIdx];
  if (!ep) return null;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-border bg-surface-1 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(59,130,246,0.15)" }}>
              <FileText className="w-5 h-5" style={{ color: SC }} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">剧本创作</h1>
              <p className="text-xs text-muted-foreground">Stage 1 · v{script.version} · {script.episode_count}集{script.scene_count}场</p>
            </div>
            <div className="flex items-center gap-2 ml-4 px-3 py-1.5 rounded-full bg-surface-2 border border-border">
              <div className={`w-2 h-2 rounded-full ${script.latest_verdict === "approved_with_minor" ? "bg-warning" : "bg-success"}`} />
              <span className="text-sm font-semibold">{script.latest_score}分</span>
              <span className="text-xs text-muted-foreground">{script.latest_verdict === "approved_with_minor" ? "待人工确认" : "已通过"}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all">
              <RefreshCw className="w-4 h-4" /> 重新生成
            </button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-stage-script)] text-white hover:opacity-90 transition-opacity animate-pulse-glow">
              <Zap className="w-4 h-4" /> 继续生成
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Main: Episodes + Scenes */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Episode tabs */}
          <div className="shrink-0 px-6 pt-4 pb-3 flex items-center gap-2 border-b border-border/50">
            {script.episodes.map((e, i) => (
              <button key={i} onClick={() => { setEpIdx(i); setExpanded(0); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  i === epIdx ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                }`}
                style={i === epIdx ? { backgroundColor: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)" } : {}}
              >
                第{e.episode_index}集<span className="block text-[10px] text-muted-foreground font-normal">{e.scenes.length}场</span>
              </button>
            ))}
          </div>

          {/* Episode info */}
          <div className="shrink-0 px-6 py-4 space-y-2">
            <h2 className="text-base font-semibold">{ep.title}</h2>
            <p className="text-sm text-muted-foreground">{ep.summary}</p>
            {ep.hook && (
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-blue-500/5 border border-blue-500/20">
                <Zap className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div><span className="text-xs font-semibold text-blue-400">HOOK</span><p className="text-sm text-muted-foreground">{ep.hook}</p></div>
              </div>
            )}
            {ep.cliffhanger && (
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-orange-500/5 border border-orange-500/20">
                <Eye className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
                <div><span className="text-xs font-semibold text-orange-400">CLIFFHANGER</span><p className="text-sm text-muted-foreground">{ep.cliffhanger}</p></div>
              </div>
            )}
          </div>

          {/* Scene cards */}
          <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-2">
            {ep.scenes.map((sc, i) => (
              <div key={sc.scene_id} className="rounded-xl border border-border bg-surface-1 overflow-hidden transition-all"
                style={expanded === i ? { borderColor: "rgba(59,130,246,0.4)" } : {}}>
                <button onClick={() => setExpanded(expanded === i ? null : i)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-2 transition-colors">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono font-bold"
                    style={{ backgroundColor: "rgba(59,130,246,0.15)", color: SC }}>{sc.scene_index}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{sc.location.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-muted-foreground">{sc.location.time_of_day}</span>
                      {sc.location.mood && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-muted-foreground">{sc.location.mood}</span>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{sc.content.segments.length}片段 · {sc.characters_present.map(c=>c.character_ref).join(" · ")}</p>
                  </div>
                  {expanded === i ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                </button>
                {expanded === i && (
                  <div className="border-t border-border animate-fade-in">
                    {sc.content.segments.map((seg, j) => (
                      <div key={j} className={`px-4 py-3 flex items-start gap-3 ${seg.type==="dialogue"?"bg-surface-2/50":seg.type==="action"?"bg-blue-500/5":"bg-surface-3/50"}`}>
                        <span className={`shrink-0 mt-0.5 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                          seg.type==="dialogue"?"bg-purple-500/20 text-purple-400":seg.type==="action"?"bg-blue-500/20 text-blue-400":"bg-gray-500/20 text-gray-400"}`}>
                          {seg.type==="narration"?"旁白":seg.type==="dialogue"?"对白":seg.type==="action"?"动作":seg.type==="inner_monologue"?"独白":seg.type}
                        </span>
                        <div className="flex-1 min-w-0">
                          {seg.character_ref && <span className="text-xs font-semibold text-purple-400">{seg.character_ref}</span>}
                          <p className={`text-sm leading-relaxed ${seg.type==="narration"?"text-muted-foreground italic":"text-foreground"}`}>{seg.text}</p>
                        </div>
                        <div className="shrink-0 flex flex-col items-end gap-1">
                          {seg.emotion_tag && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400">{seg.emotion_tag}</span>}
                          {seg.action_tag && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400">{seg.action_tag}</span>}
                        </div>
                      </div>
                    ))}
                    {sc.visual_emphasis.length>0 && (
                      <div className="px-4 py-2 bg-surface-3/50 border-t border-border flex items-center gap-2 flex-wrap">
                        <Eye className="w-3.5 h-3.5 text-muted-foreground" /><span className="text-xs text-muted-foreground">视觉强调:</span>
                        {sc.visual_emphasis.map((v,k)=><span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">{v}</span>)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right sidebar: Indexes + Review */}
        <div className="w-80 shrink-0 border-l border-border bg-surface-1 flex flex-col overflow-hidden">
          <div className="shrink-0 border-b border-border"><div className="px-4 py-3 flex items-center gap-2"><Users className="w-4 h-4 text-muted-foreground"/><h3 className="text-sm font-semibold">角色索引</h3></div>
            <div className="px-4 pb-3 space-y-1">
              {script.character_index.map(c=><div key={c.ref_name} className="flex items-center justify-between px-3 py-2 rounded-lg bg-surface-2"><div><span className="text-sm font-medium">{c.ref_name}</span><span className={`text-[10px] ml-2 px-1.5 py-0.5 rounded-full ${c.role_type==="protagonist"?"bg-amber-500/15 text-amber-400":c.role_type==="antagonist"?"bg-red-500/15 text-red-400":"bg-surface-3 text-muted-foreground"}`}>{c.role_type==="protagonist"?"主角":c.role_type==="antagonist"?"反派":"配角"}</span></div><span className="text-[10px] text-muted-foreground">{c.scene_count}场</span></div>)}
            </div>
          </div>
          <div className="shrink-0 border-b border-border"><div className="px-4 py-3 flex items-center gap-2"><MapPin className="w-4 h-4 text-muted-foreground"/><h3 className="text-sm font-semibold">场景索引</h3></div>
            <div className="px-4 pb-3 space-y-1">{script.location_index.map(l=><div key={l.name} className="flex items-center justify-between px-3 py-1.5 text-sm"><span className="text-muted-foreground">{l.name}</span><span className="text-[10px] text-muted-foreground">{l.scene_count}场</span></div>)}</div>
          </div>
          <div className="flex-1 overflow-hidden flex flex-col">
            <button onClick={()=>setShowReview(!showReview)} className="shrink-0 px-4 py-3 flex items-center justify-between hover:bg-surface-2"><div className="flex items-center gap-2"><MessageSquare className="w-4 h-4 text-muted-foreground"/><h3 className="text-sm font-semibold">审查记录</h3></div>{showReview?<ChevronUp className="w-4 h-4 text-muted-foreground"/>:<ChevronDown className="w-4 h-4 text-muted-foreground"/>}</button>
            {showReview && <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2 animate-fade-in">
              {script.review_history.map((r,i)=><div key={i} className="p-3 rounded-lg bg-surface-2 border border-border"><div className="flex items-center justify-between mb-1.5"><span className="text-xs font-semibold">Round {r.round}</span><span className={`flex items-center gap-1 text-xs font-medium ${r.verdict.includes("approved")?"text-success":"text-warning"}`}>{r.verdict.includes("approved")?<CheckCircle className="w-3 h-3"/>:<AlertTriangle className="w-3 h-3"/>}{r.merged_score}分</span></div><div className="flex gap-3 text-[10px] text-muted-foreground"><span>剧评:{r.drama_critic_score}</span><span>风格:{r.style_guard_score}</span>{r.blocker_count>0&&<span className="text-destructive">{r.blocker_count}blocker</span>}</div></div>)}
              <div className="flex gap-2 pt-2">
                <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-success/10 border border-success/30 text-success text-sm font-medium hover:bg-success/20"><ThumbsUp className="w-4 h-4"/>通过</button>
                <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm font-medium hover:bg-destructive/20"><ThumbsDown className="w-4 h-4"/>打回</button>
              </div>
            </div>}
          </div>
        </div>
      </div>
    </div>
  );
}
