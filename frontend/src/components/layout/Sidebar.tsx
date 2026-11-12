import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckSquare,
  Database,
  History,
  LayoutDashboard,
  LogOut,
  Map,
  Settings,
  Shield,
  TrendingUp,
  X,
} from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { cn, humanizeKey } from "../../lib/utils";

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

interface SidebarProps {
  open?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ open = false, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const nav = (
    <>
      <div className="flex items-center justify-between gap-3 border-b p-4">
        <Link to="/overview" className="flex items-center gap-3 min-w-0" onClick={onClose}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--brand-mark))] font-display text-sm font-bold tracking-wide text-primary-foreground shadow-sm">
            SH
          </div>
          <div className="min-w-0">
            <h1 className="truncate font-display text-sm font-semibold tracking-tight">SentinelHealth</h1>
            <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Early Warning</p>
          </div>
        </Link>
        {onClose ? (
          <button
            type="button"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground lg:hidden"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.href ||
            (item.href !== "/overview" && location.pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              to={item.href}
              onClick={onClose}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t bg-muted/40 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="min-w-0 truncate pr-1">
            <p className="truncate text-xs font-semibold">{user?.display_name || user?.email || "Operator"}</p>
            <p className="truncate text-[10px] capitalize text-muted-foreground">
              {humanizeKey(user?.current_role) || "Analyst"}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-background hover:text-destructive"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center justify-between border-t border-border/50 pt-1 text-[10px] text-muted-foreground">
          <span>Asia/Kolkata</span>
          <span className="font-mono">v0.1.0</span>
        </div>
      </div>
    </>
  );

  return (
    <>
      <aside className="hidden h-screen w-64 shrink-0 select-none flex-col border-r bg-card/95 backdrop-blur lg:flex">
        {nav}
      </aside>

      <div
        className={cn(
          "fixed inset-0 z-40 bg-foreground/40 backdrop-blur-[2px] transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-screen w-72 max-w-[85vw] select-none flex-col border-r bg-card shadow-panel transition-transform duration-200 lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-hidden={!open}
      >
        {nav}
      </aside>
    </>
  );
};
