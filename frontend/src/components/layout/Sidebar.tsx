import { NavLink } from "react-router-dom";
import { Compass, BarChart3, BookOpen, Wind } from "lucide-react";
import { SystemStatus } from "./SystemStatus";
import { cn } from "@/lib/utils";

interface SidebarProps {
  lastLatencyMs?: number;
  onNavigate?: () => void;
}

export function Sidebar({ lastLatencyMs, onNavigate }: SidebarProps) {
  const links = [
    { to: "/", label: "Decision Cockpit", icon: Compass, exact: true },
    { to: "/accuracy", label: "Accuracy Studio", icon: BarChart3, exact: false },
    { to: "/methodology", label: "Methodology", icon: BookOpen, exact: false },
  ];

  return (
    <aside className="flex h-full w-64 flex-col justify-between border-r border-[#E2E0D8] bg-[#F7F6F1] p-4">
      <div className="space-y-6">
        {/* Brand Mark */}
        <div className="flex items-center gap-2.5 px-2 py-1">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#174D3E] text-white shadow-xs">
            <Wind className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-[#141F1B]">WindScope</h1>
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#5A6B64]">Day-ahead Intelligence</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={onNavigate}
                end={link.exact}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[#DCE8DF] text-[#174D3E] font-semibold shadow-2xs"
                      : "text-[#5A6B64] hover:bg-[#F0EFEA] hover:text-[#141F1B]"
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* System Status in Sidebar footer */}
      <div className="pt-4">
        <SystemStatus lastLatencyMs={lastLatencyMs} />
      </div>
    </aside>
  );
}
