import { Outlet, NavLink } from "react-router-dom";
import { Clapperboard, Home, Plus } from "lucide-react";

const navItems = [
  { to: "/", label: "项目列表", icon: <Home className="w-5 h-5" /> },
];

export function Layout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-56 border-r bg-card flex flex-col">
        <div className="p-4 border-b flex items-center gap-2">
          <Clapperboard className="w-6 h-6 text-primary" />
          <span className="font-semibold text-sm">AI 漫剧创作</span>
        </div>

        <nav className="p-2 flex flex-col gap-1 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
              end={item.to === "/"}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}

          <div className="mt-2 px-3 py-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
              创作流程
            </p>
          </div>
          <NavLink
            to="/"
            className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Plus className="w-5 h-5" />
            新建项目
          </NavLink>
        </nav>

        <div className="p-3 border-t text-xs text-muted-foreground">
          v0.1.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
