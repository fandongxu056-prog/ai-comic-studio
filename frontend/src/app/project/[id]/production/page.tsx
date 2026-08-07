import { useParams } from "react-router-dom";

export function ProductionWorkspace() {
  const { id } = useParams();
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">制作合成</h1>
      <p className="text-muted-foreground mb-6">
        Pipeline 确定性执行：ImageGen → VideoGen → TTSGen → Compositor
      </p>
      <div className="border rounded-lg p-12 text-center text-muted-foreground">
        制作合成工作台 — 即将实现
      </div>
    </div>
  );
}
