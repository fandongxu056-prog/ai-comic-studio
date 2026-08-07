import { useNavigate } from "react-router-dom";
import { Plus, Clapperboard, Play } from "lucide-react";

export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">AI 漫剧创作平台</h1>
          <p className="text-muted-foreground mt-1">
            从剧本到成片，一站式 AI 漫剧创作
          </p>
        </div>
        <button
          onClick={() => navigate("/project/new")}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" />
          新建项目
        </button>
      </div>

      {/* Empty state */}
      <div className="border rounded-lg p-12 text-center">
        <Clapperboard className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-40" />
        <h2 className="text-lg font-semibold mb-2">还没有项目</h2>
        <p className="text-muted-foreground mb-4">
          创建你的第一个 AI 漫剧项目，开始创作之旅
        </p>
        <button
          onClick={() => navigate("/project/new")}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
        >
          <Play className="w-4 h-4" />
          开始创作
        </button>
      </div>
    </div>
  );
}
