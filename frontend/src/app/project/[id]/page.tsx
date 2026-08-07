import { useParams, useNavigate } from "react-router-dom";
import { Script, Image, LayoutGrid, Film } from "lucide-react";

const stages = [
  {
    key: "script",
    label: "剧本创作",
    description: "编写和审查剧本",
    icon: <Script className="w-8 h-8" />,
    color: "text-blue-500",
    bgColor: "bg-blue-50",
  },
  {
    key: "assets",
    label: "资产设计",
    description: "角色、场景、道具设计",
    icon: <Image className="w-8 h-8" />,
    color: "text-purple-500",
    bgColor: "bg-purple-50",
  },
  {
    key: "storyboard",
    label: "分镜脚本",
    description: "镜头拆解和构图设计",
    icon: <LayoutGrid className="w-8 h-8" />,
    color: "text-orange-500",
    bgColor: "bg-orange-50",
  },
  {
    key: "production",
    label: "制作合成",
    description: "AI 生成和视频合成",
    icon: <Film className="w-8 h-8" />,
    color: "text-green-500",
    bgColor: "bg-green-50",
  },
];

export function ProjectDashboard() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">项目概览</h1>
        <p className="text-muted-foreground mt-1">项目 ID: {id}</p>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center gap-2 mb-8">
        {stages.map((stage, i) => (
          <div key={stage.key} className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full border-2 border-muted flex items-center justify-center text-xs text-muted-foreground">
              {i + 1}
            </div>
            <span className="text-sm text-muted-foreground">{stage.label}</span>
            {i < stages.length - 1 && (
              <div className="w-8 h-px bg-muted" />
            )}
          </div>
        ))}
      </div>

      {/* Stage cards */}
      <div className="grid grid-cols-2 gap-4">
        {stages.map((stage) => (
          <button
            key={stage.key}
            onClick={() => navigate(`/project/${id}/${stage.key}`)}
            className="flex items-start gap-4 p-5 border rounded-lg text-left hover:border-primary hover:shadow-sm transition-all"
          >
            <div className={`p-3 rounded-lg ${stage.bgColor}`}>
              <div className={stage.color}>{stage.icon}</div>
            </div>
            <div>
              <h3 className="font-semibold">{stage.label}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {stage.description}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
