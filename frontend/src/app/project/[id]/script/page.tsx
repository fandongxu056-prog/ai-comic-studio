import { useParams } from "react-router-dom";

export function ScriptWorkspace() {
  const { id } = useParams();

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">剧本创作</h1>
          <p className="text-muted-foreground mt-1">
            Multi-Agent 协作：ScriptWriter · DramaCritic · StyleGuard
          </p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 border rounded-md text-sm hover:bg-muted transition-colors">
            导入小说
          </button>
          <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90">
            开始创作
          </button>
        </div>
      </div>

      {/* Placeholder — will be implemented in Step 5 */}
      <div className="border rounded-lg p-12 text-center text-muted-foreground">
        剧本创作工作台 — 即将实现
      </div>
    </div>
  );
}
