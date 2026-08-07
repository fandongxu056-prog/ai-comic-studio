import { useParams } from "react-router-dom";

export function AssetWorkspace() {
  const { id } = useParams();
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">资产设计</h1>
      <p className="text-muted-foreground mb-6">
        Multi-Agent 协作：CharDesigner · SceneDesigner · PropDesigner · ConsistencyAuditor
      </p>
      <div className="border rounded-lg p-12 text-center text-muted-foreground">
        资产设计工作台 — 即将实现
      </div>
    </div>
  );
}
