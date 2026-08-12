import { useState } from "react";
import { Outlet, NavLink, useNavigate, useParams, useLocation } from "react-router-dom";
import {
  Clapperboard,
  Home,
  FileText,
  Image,
  LayoutGrid,
  Film,
  Settings,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  User,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";

const stageNav = (projectId: string) => [
  {
    to: `/project/${projectId}/script`,
    label: "剧本创作",
    icon: <FileText className="w-4 h-4" />,
    color: "var(--color-stage-script)",
    stage: "script",
  },
  {
    to: `/project/${projectId}/assets`,
    label: "资产设计",
    icon: <Image className="w-4 h-4" />,
    color: "var(--color-stage-assets)",
    stage: "assets",
  },
  {
    to: `/project/${projectId}/storyboard`,
    label: "分镜设计",
    icon: <LayoutGrid className="w-4 h-4" />,
    color: "var(--color-stage-storyboard)",
    stage: "storyboard",
  },
  {
    to: `/project/${projectId}/production`,
    label: "制作合成",
    icon: <Film className="w-4 h-4" />,
    color: "var(--color-stage-production)",
    stage: "production",
  },
];

export function Layout() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const isProjectPage = location.pathname.includes("/project/");
  const { user, logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-border bg-surface-1 transition-all duration-300 ${
          collapsed ? "w-14" : "w-56"
        }`}
      >
        {/* Brand */}
        <div className="p-3 border-b border-border flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
            <Clapperboard className="w-4 h-4 text-primary" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-sm tracking-tight text-foreground">
              AI 漫剧创作
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="ml-auto p-1 rounded-md hover:bg-surface-3 text-muted-foreground hover:text-foreground transition-colors"
          >
            {collapsed ? (
              <PanelLeft className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 flex flex-col gap-0.5 overflow-y-auto">
          {/* Home */}
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-all duration-200 ${
                isActive
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
              } ${collapsed ? "justify-center" : ""}`
            }
            title="项目列表"
          >
            <Home className="w-4 h-4 shrink-0" />
            {!collapsed && "项目列表"}
          </NavLink>

          {/* Stage Navigation (only on project pages) */}
          {isProjectPage && id && (
            <>
              {!collapsed && (
                <p className="mt-4 mb-1 px-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                  创作管线
                </p>
              )}

              {stageNav(id).map((item, i) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-all duration-200 group ${
                      isActive
                        ? "bg-surface-3 text-foreground font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                    } ${collapsed ? "justify-center" : ""}`
                  }
                  title={item.label}
                >
                  <div
                    className="w-1 h-4 rounded-full shrink-0 transition-colors"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="shrink-0" style={{ color: item.color }}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      <span
                        className="text-[10px] font-mono text-muted-foreground"
                      >
                        S{i + 1}
                      </span>
                    </>
                  )}
                </NavLink>
              ))}
            </>
          )}

          {/* Dashboard link */}
          {isProjectPage && id && (
            <NavLink
              to={`/project/${id}`}
              end
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-2 mt-2 rounded-lg text-sm transition-all ${
                  isActive
                    ? "bg-surface-3 text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                } ${collapsed ? "justify-center" : ""}`
              }
              title="项目概览"
            >
              <Settings className="w-4 h-4 shrink-0" />
              {!collapsed && "项目概览"}
            </NavLink>
          )}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-border shrink-0">
          {user ? (
            <div className={collapsed ? "flex justify-center" : ""}>
              {collapsed ? (
                <button onClick={logout} className="p-1.5 rounded-lg hover:bg-surface-3 text-muted-foreground hover:text-destructive transition-colors" title="退出登录">
                  <LogOut className="w-4 h-4" />
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                    <User className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{user.display_name || user.username}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
                  </div>
                  <button onClick={logout} className="p-1 rounded-md hover:bg-surface-3 text-muted-foreground hover:text-destructive transition-colors" title="退出登录">
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            !collapsed ? (
              <button onClick={() => navigate("/login")} className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors">
                <User className="w-4 h-4" /> 登录
              </button>
            ) : (
              <div className="flex justify-center">
                <button onClick={() => navigate("/login")} className="p-1.5 rounded-lg hover:bg-surface-3 text-muted-foreground hover:text-foreground transition-colors" title="登录">
                  <User className="w-4 h-4" />
                </button>
              </div>
            )
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden bg-background">
        <Outlet />
      </main>
    </div>
  );
}
