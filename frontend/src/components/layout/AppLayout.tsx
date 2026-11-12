import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { ScreeningNotice } from "./ScreeningNotice";
import { ThemeToggle } from "./ThemeToggle";
import { Button } from "../ui/button";
import { useAuth } from "../../auth/AuthProvider";
import { humanizeKey } from "../../lib/utils";

export const AppLayout: React.FC = () => {
  const [navOpen, setNavOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="flex h-screen overflow-hidden bg-transparent">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <ScreeningNotice />
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b bg-card/80 px-4 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0">
              <p className="truncate font-display text-sm font-semibold tracking-tight lg:hidden">
                SentinelHealth
              </p>
              <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" aria-hidden />
                <span>Live console · ensemble screening online</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden text-right md:block">
              <p className="truncate text-xs font-semibold">{user?.display_name}</p>
              <p className="truncate text-[10px] capitalize text-muted-foreground">
                {humanizeKey(user?.current_role)}
              </p>
            </div>
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
