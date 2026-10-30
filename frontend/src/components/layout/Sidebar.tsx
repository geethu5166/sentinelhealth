import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckSquare,
  Database,
  History,
  LayoutDashboard,
  LogOut,
  Map,
  Settings,
  Shield,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { cn } from "../../lib/utils";

const NAV_ITEMS = [
  { name: "Overview", href: "/overview", icon: LayoutDashboard },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
  { name: "Map", href: "/map", icon: Map },
  { name: "Signals", href: "/signals", icon: Activity },
  { name: "Tasks", href: "/tasks", icon: CheckSquare },
  { name: "Sources", href: "/sources", icon: Database },
  { name: "Validation", href: "/validation", icon: History },
  { name: "Impact", href: "/impact", icon: TrendingUp },
  { name: "Governance", href: "/governance", icon: Shield },
  { name: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 border-r bg-card flex flex-col h-screen select-none">
      <div className="p-4 border-b flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-black tracking-wider">
          SH
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-tight">SentinelHealth</h1>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Early Warning</p>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.href || (item.href !== "/overview" && location.pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t bg-muted/40">
        <div className="flex items-center justify-between mb-2">
          <div className="truncate pr-2">
            <p className="text-xs font-semibold truncate">{user?.display_name || user?.email || "Demo User"}</p>
            <p className="text-[10px] text-muted-foreground truncate capitalize">
              {user?.current_role?.replace(/_/g, " ") || "Analyst"}
            </p>
          </div>
          <button
            onClick={logout}
            className="text-muted-foreground hover:text-destructive p-1 rounded"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
        <div className="text-[10px] text-muted-foreground flex items-center justify-between pt-1 border-t border-border/50">
          <span>Asia/Kolkata (UTC+5:30)</span>
          <span className="font-mono">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
};

