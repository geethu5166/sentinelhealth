import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Activity, ArrowRight, Loader2, Shield } from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { cn } from "../lib/utils";

const DEMO_ROLES = [
  {
    role: "workplace_safety_manager",
    email: "safety@demo.local",
    name: "Vikram Patel",
    title: "Workplace Safety Manager",
    focus: "Site playbooks, heat & PPE response",
  },
  {
    role: "public_health_analyst",
    email: "analyst@demo.local",
    name: "Dr. Ananya Sharma",
    title: "Public Health Lead",
    focus: "District signals, episode triage",
  },
  {
    role: "occupational_health_analyst",
    email: "ohanalyst@demo.local",
    name: "Rajesh Kumar",
    title: "Occupational Health Analyst",
    focus: "Workforce absence & exposure review",
  },
  {
    role: "privacy_officer",
    email: "privacy@demo.local",
    name: "Meera Iyer",
    title: "Privacy Officer",
    focus: "Suppression policy & disclosure controls",
  },
];

export const LoginPage: React.FC = () => {
  const { loginAsDemoUser, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  const handleDemoLogin = async (role: string, email: string) => {
    setError(null);
    setPendingEmail(email);
    try {
      await loginAsDemoUser(role, email);
      navigate("/overview");
    } catch {
      setError("Could not start the demo session. Try again.");
    } finally {
      setPendingEmail(null);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden login-atmosphere text-white">
      <div className="pointer-events-none absolute inset-0 surface-grid opacity-[0.12]" />
      <div className="pointer-events-none absolute -left-24 top-24 h-72 w-72 rounded-full bg-teal-400/20 blur-3xl animate-soft-pulse" />
      <div className="pointer-events-none absolute -right-16 bottom-10 h-80 w-80 rounded-full bg-amber-300/10 blur-3xl" />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col justify-center gap-10 px-6 py-12 lg:flex-row lg:items-center lg:gap-16">
        <section className="animate-fade-up max-w-xl space-y-6 lg:flex-1">
          <div className="inline-flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 font-display text-xl font-bold tracking-wide ring-1 ring-white/20 backdrop-blur">
              SH
            </div>
            <div>
              <p className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">SentinelHealth</p>
              <p className="text-xs uppercase tracking-[0.22em] text-teal-100/80">Early Warning Console</p>
            </div>
          </div>

          <h1 className="font-display text-balance text-3xl font-semibold leading-tight tracking-tight text-white sm:text-4xl">
            Population & workforce health surveillance for accountable prevention.
          </h1>
          <p className="max-w-lg text-sm leading-relaxed text-teal-50/80 sm:text-base">
            Aggregate environmental, clinical, and workplace signals into privacy-preserving early warnings —
            with role-based review, playbooks, and audit trails for Indian public and occupational health teams.
          </p>

          <div className="flex flex-wrap gap-3 text-[11px] text-teal-100/75">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1">
              <Shield className="h-3.5 w-3.5" /> Small-cell suppression
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1">
              <Activity className="h-3.5 w-3.5" /> Multi-signal EWMA screening
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1">
              Asia/Kolkata · Synthetic demo data
            </span>
          </div>
        </section>

        <section className="animate-fade-up w-full max-w-md lg:flex-1" style={{ animationDelay: "120ms" }}>
          <div className="rounded-2xl border border-white/15 bg-white/95 p-6 text-foreground shadow-panel backdrop-blur dark:bg-card/95">
            <div className="mb-5 space-y-1">
              <h2 className="font-display text-lg font-semibold tracking-tight">Enter the decision console</h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Choose a demo identity. Sessions stay in this browser tab and use synthetic fixtures only.
              </p>
            </div>

            <ul className="space-y-2">
              {DEMO_ROLES.map((demo) => {
                const busy = pendingEmail === demo.email;
                return (
                  <li key={demo.email}>
                    <button
                      type="button"
                      aria-label={`${demo.name}, ${demo.title}`}
                      disabled={!!pendingEmail}
                      onClick={() => handleDemoLogin(demo.role, demo.email)}
                      className={cn(
                        "group flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-card px-3.5 py-3 text-left transition-all",
                        "hover:border-primary/40 hover:bg-secondary/70 hover:shadow-sm",
                        "disabled:cursor-wait disabled:opacity-70"
                      )}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">{demo.name}</p>
                        <p className="truncate text-[11px] text-muted-foreground">{demo.title}</p>
                        <p className="mt-0.5 truncate text-[10px] text-muted-foreground/80">{demo.focus}</p>
                      </div>
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-hover:translate-x-0.5">
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>

            {error ? (
              <p role="alert" className="mt-3 text-xs text-destructive">
                {error}
              </p>
            ) : null}

            <div className="mt-5 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2.5 text-[11px] leading-relaxed text-amber-900 dark:text-amber-200">
              <strong>Demonstration prototype.</strong> Not clinically validated, HIPAA/DISHA compliant, or intended
              for real patient data, employment decisions, or diagnosis.
            </div>

            <p className="mt-4 text-center text-[10px] text-muted-foreground">
              Keycloak OIDC is available in the full Docker stack; this MVP uses demo tokens for local walkthroughs.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};
