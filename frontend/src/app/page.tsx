import { useState, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, Clapperboard, Play, FileText, Image, LayoutGrid, Film,
  ChevronRight, X, Loader2, Sparkles,
} from "lucide-react";
import { api, ProjectResponse, ProjectListResponse, ProjectCreateInput } from "@/services/api";
import { useAuthStore } from "@/stores/auth-store";

const stageColors: Record<string, string> = {
  script: "var(--color-stage-script)",
  assets: "var(--color-stage-assets)",
  storyboard: "var(--color-stage-storyboard)",
  production: "var(--color-stage-production)",
  complete: "var(--color-success)",
};
const stageLabels: Record<string, string> = {
  not_started: "未开始", in_progress: "进行中", review: "待审批",
  locked: "已锁定", revision: "修改中", complete: "已完成",
  completed: "已完成", partial_complete: "部分完成", failed: "失败",
};
const stageIcons: Record<string, any> = {
  script: FileText, assets: Image, storyboard: LayoutGrid, production: Film,
};

export function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  // Create form state
  const [title, setTitle] = useState("");
  const [sourceType, setSourceType] = useState("original_idea");
  const [sourceContent, setSourceContent] = useState("");
  const [genrePrimary, setGenrePrimary] = useState("urban");
  const [artStyle, setArtStyle] = useState("anime");
  const [episodes, setEpisodes] = useState(1);
  const [duration, setDuration] = useState(120);

  const loadProjects = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get<ProjectListResponse>("/projects/");
      setProjects(data.data || []);
    } catch (e: any) {
      setError(e.message || "加载项目失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) loadProjects();
    else setLoading(false);
  }, [isAuthenticated]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      const input: ProjectCreateInput = {
        title: title.trim(),
        source_type: sourceType,
        source_content: sourceContent.trim(),
        genre: { primary: genrePrimary, sub_tags: [] },
        target_spec: {
          format: "horizontal_standard",
          aspect_ratio: "16:9",
          total_duration_seconds: duration * episodes,
          episode_count: episodes,
          duration_per_episode_seconds: duration,
        },
        style_preference: { art_style: artStyle },
      };
      const project = await api.post<ProjectResponse>("/projects/", input);
      setShowCreate(false);
      setTitle(""); setSourceContent("");
      await loadProjects();
      navigate(`/project/${project.id}`);
    } catch (err: any) {
      setError(err.message || "创建失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI 漫剧创作平台</h1>
          <p className="text-muted-foreground mt-1">
            {user ? `你好，${user.display_name || user.username} — 从剧本到成片，一站式 AI 创作` : "从剧本到成片 — 一站式 AI 漫剧全自动创作管线"}
          </p>
        </div>
        {isAuthenticated ? (
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary-hover transition-all shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4" /> 新建项目
          </button>
        ) : (
          <button onClick={() => navigate("/login")}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary-hover transition-all">
            <Play className="w-4 h-4" /> 登录开始创作
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">{error}</div>
      )}

      {/* Create project modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setShowCreate(false)}>
          <div className="w-full max-w-lg mx-4 p-6 rounded-2xl bg-surface-1 border border-border animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Sparkles className="w-5 h-5 text-primary"/>新建漫剧项目</h2>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded-md hover:bg-surface-2 text-muted-foreground"><X className="w-4 h-4"/></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">作品标题 *</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none focus:border-primary transition-all"
                  placeholder="如：戒指之谜" required autoFocus />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">题材</label>
                  <select value={genrePrimary} onChange={(e) => setGenrePrimary(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none">
                    <option value="urban">都市</option>
                    <option value="xianxia">仙侠</option>
                    <option value="fantasy">奇幻</option>
                    <option value="sci_fi">科幻</option>
                    <option value="wuxia">武侠</option>
                    <option value="romance">言情</option>
                    <option value="comedy">喜剧</option>
                    <option value="mystery">悬疑</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">视觉风格</label>
                  <select value={artStyle} onChange={(e) => setArtStyle(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none">
                    <option value="anime">🎨 日漫动画</option>
                    <option value="realistic">🎬 真人写实</option>
                    <option value="semi_realistic">✨ 半写实CG</option>
                    <option value="3d_render">🧊 3D渲染</option>
                    <option value="comic_book">💥 美漫漫画</option>
                    <option value="ink_wash">🖌️ 水墨画</option>
                    <option value="illustration">🖼️ 精美插画</option>
                    <option value="cartoon">😄 卡通风格</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">输入类型</label>
                <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none">
                  <option value="original_idea">原创创意</option>
                  <option value="synopsis">故事梗概</option>
                  <option value="outline">剧情大纲</option>
                  <option value="novel_excerpt">小说片段</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">创意描述 *</label>
                <textarea value={sourceContent} onChange={(e) => setSourceContent(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none focus:border-primary transition-all resize-none"
                  placeholder="描述你的故事创意，如：少年在垃圾场捡到神秘戒指，能看到死者最后3秒的记忆……" required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">集数</label>
                  <input type="number" min={1} max={200} value={episodes} onChange={(e) => setEpisodes(parseInt(e.target.value) || 1)}
                    className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">每集时长（秒）</label>
                  <input type="number" min={30} max={600} value={duration} onChange={(e) => setDuration(parseInt(e.target.value) || 120)}
                    className="w-full px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm focus:outline-none" />
                </div>
              </div>
              <button type="submit" disabled={creating || !title.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary-hover transition-all disabled:opacity-50">
                {creating ? <><Loader2 className="w-4 h-4 animate-spin"/>创建中...</> : "创建并开始创作"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Project list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 rounded-xl shimmer" />)}
        </div>
      ) : projects.length > 0 ? (
        <div className="space-y-3">
          {projects.map((p) => {
            const Icon = stageIcons[p.current_stage as keyof typeof stageIcons] || FileText;
            const color = stageColors[p.current_stage] || "var(--color-muted-foreground)";
            const stageStatus = p.stages?.[p.current_stage as keyof typeof p.stages]?.status || "not_started";
            return (
              <button key={p.id} onClick={() => navigate(`/project/${p.id}`)}
                className="w-full flex items-center gap-5 p-5 rounded-xl bg-surface-1 border border-border hover:border-[var(--color-border-hover)] hover:bg-surface-2 transition-all text-left group">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: `${color}15` }}>
                  <Icon className="w-6 h-6" style={{ color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{p.title}</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-2 text-muted-foreground">
                      {p.genre && typeof p.genre === "object" && "primary" in p.genre ? String((p.genre as any).primary) : p.source_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-xs text-muted-foreground">{stageLabels[stageStatus] || stageStatus}</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">{p.id}</span>
                    <span className="text-xs text-muted-foreground">{p.episode_count}集 · {p.aspect_ratio}</span>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
              </button>
            );
          })}
        </div>
      ) : isAuthenticated ? (
        <div className="border border-border rounded-xl p-16 text-center bg-surface-1">
          <Clapperboard className="w-20 h-20 mx-auto mb-4 text-muted-foreground opacity-30" />
          <h2 className="text-lg font-semibold mb-2">还没有项目</h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">创建你的第一个 AI 漫剧项目，从剧本到成片，全自动管线一气呵成</p>
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary-hover transition-all">
            <Play className="w-4 h-4" /> 开始创作
          </button>
        </div>
      ) : (
        <div className="border border-border rounded-xl p-16 text-center bg-surface-1">
          <Clapperboard className="w-20 h-20 mx-auto mb-4 text-muted-foreground opacity-30" />
          <h2 className="text-lg font-semibold mb-2">欢迎使用 AI 漫剧创作平台</h2>
          <p className="text-muted-foreground mb-6">登录后开始你的 AI 漫剧创作之旅</p>
          <button onClick={() => navigate("/login")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary-hover transition-all">
            <Play className="w-4 h-4" /> 登录 / 注册
          </button>
        </div>
      )}
    </div>
  );
}
