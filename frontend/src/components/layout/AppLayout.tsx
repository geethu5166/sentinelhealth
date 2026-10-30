import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { SyntheticBanner } from "./SyntheticBanner";
import { ThemeToggle } from "./ThemeToggle";

export const AppLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <SyntheticBanner />
        <header className="h-14 border-b bg-card flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Surveillance Engine Online (Local Mode)</span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

