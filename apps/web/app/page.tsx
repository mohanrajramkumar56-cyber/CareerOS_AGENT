"use client";

/**
 * CareerOS — Full Dashboard (Phase 8)
 *
 * Data-driven dashboard showing real stats from the API.
 * Fetches from GET /api/v1/dashboard/stats on mount.
 */

import { useState, useEffect } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DashboardStats {
  jobs_discovered: number;
  jobs_matched: number;
  jobs_eligible: number;
  resumes_generated: number;
  applications_total: number;
  applications_pending_approval: number;
  applications_submitted: number;
  applications_draft: number;
}

interface ActivityItem {
  type: "application" | "resume" | "match";
  status?: string;
  title?: string;
  template?: string;
  timestamp: string | null;
  resource_id: string;
}

// ── API helpers ───────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/api/v1/dashboard/stats`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function fetchActivity(): Promise<{ items: ActivityItem[] }> {
  const res = await fetch(`${API_BASE}/api/v1/dashboard/activity`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function timeAgo(ts: string | null): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  description,
  accent = "gray",
  loading = false,
}: {
  label: string;
  value: number;
  description?: string;
  accent?: "blue" | "green" | "yellow" | "red" | "purple" | "gray";
  loading?: boolean;
}) {
  const borders = {
    blue: "border-l-blue-500",
    green: "border-l-green-500",
    yellow: "border-l-yellow-500",
    red: "border-l-red-500",
    purple: "border-l-purple-500",
    gray: "border-l-gray-600",
  };

  return (
    <article
      className={`bg-gray-900 rounded-lg p-5 border border-gray-800 border-l-4 ${borders[accent]}`}
      aria-label={`${label}: ${loading ? "loading" : value}`}
    >
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
      {loading ? (
        <div className="h-8 w-16 bg-gray-800 rounded animate-pulse mt-2" />
      ) : (
        <p className="text-3xl font-bold text-white mt-1">{value.toLocaleString()}</p>
      )}
      {description && <p className="text-xs text-gray-600 mt-1">{description}</p>}
    </article>
  );
}

// ── Mini bar chart (pure CSS) ─────────────────────────────────────────────────

function MiniBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-24 truncate">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{value}</span>
    </div>
  );
}

// ── Activity Feed ─────────────────────────────────────────────────────────────

function ActivityFeed({ items, loading }: { items: ActivityItem[]; loading: boolean }) {
  const typeIcon: Record<string, string> = {
    application: "📋",
    resume: "📄",
    match: "🎯",
  };

  const statusColor: Record<string, string> = {
    draft: "text-gray-400",
    pending_approval: "text-yellow-400",
    approved: "text-blue-400",
    submitted: "text-green-400",
    rejected: "text-red-400",
    withdrawn: "text-gray-500",
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="w-8 h-8 bg-gray-800 rounded" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3 bg-gray-800 rounded w-3/4" />
              <div className="h-3 bg-gray-800 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return <p className="text-sm text-gray-600 italic">No recent activity. Start by exploring jobs.</p>;
  }

  return (
    <ul className="space-y-3" aria-label="Recent activity">
      {items.map((item) => (
        <li key={`${item.type}-${item.resource_id}`} className="flex items-start gap-3">
          <span className="text-lg" aria-hidden="true">{typeIcon[item.type] ?? "·"}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-200">
              {item.type === "application" && (
                <>Application — <span className={`font-medium ${statusColor[item.status ?? ""] ?? "text-gray-400"}`}>{item.status?.replace(/_/g, " ")}</span></>
              )}
              {item.type === "resume" && (
                <>{item.title ?? "Resume"} <span className="text-gray-500">({item.template})</span></>
              )}
            </p>
            <p className="text-xs text-gray-600">{timeAgo(item.timestamp)}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

// ── Phase Status ──────────────────────────────────────────────────────────────

const PHASES = [
  { name: "Foundation", status: "complete" },
  { name: "Candidate Intelligence", status: "complete" },
  { name: "Job Intelligence", status: "complete" },
  { name: "Matching Engine", status: "complete" },
  { name: "Resume Engine", status: "complete" },
  { name: "Application Engine", status: "complete" },
  { name: "Policy + Security", status: "complete" },
  { name: "Email + Follow-up", status: "complete" },
  { name: "Dashboard", status: "complete" },
  { name: "Observability", status: "in-progress" },
  { name: "Production Hardening", status: "in-progress" },
  { name: "E2E Validation", status: "pending" },
] as const;

function PhaseTracker() {
  const complete = PHASES.filter((p) => p.status === "complete").length;
  const pct = Math.round((complete / PHASES.length) * 100);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">Build Progress</span>
        <span className="text-sm font-medium text-white">{pct}%</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2 mb-4" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {PHASES.map((phase) => {
          const dot = phase.status === "complete" ? "bg-green-500" : phase.status === "in-progress" ? "bg-yellow-400" : "bg-gray-700";
          return (
            <div key={phase.name} className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot}`} aria-hidden="true" />
              <span className="text-xs text-gray-400 truncate">{phase.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [activityLoading, setActivityLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setStatsLoading(false));

    fetchActivity()
      .then((d) => setActivity(d.items))
      .catch(() => {}) // non-critical
      .finally(() => setActivityLoading(false));
  }, []);

  const s = stats;
  const maxApps = s ? Math.max(s.applications_total, 1) : 1;

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">CareerOS — Autonomous AI Career Operating System</p>
      </header>

      {/* Error banner */}
      {error && (
        <div role="alert" className="p-3 bg-red-500/10 border border-red-700 rounded text-red-400 text-sm">
          Could not load stats from API ({error}). Is the backend running?
        </div>
      )}

      {/* Stat cards grid */}
      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">Dashboard Statistics</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Jobs Discovered" value={s?.jobs_discovered ?? 0} accent="blue" loading={statsLoading} description="In the pipeline" />
          <StatCard label="Matches Computed" value={s?.jobs_matched ?? 0} accent="purple" loading={statsLoading} description="Scored against you" />
          <StatCard label="Eligible Jobs" value={s?.jobs_eligible ?? 0} accent="green" loading={statsLoading} description="Passed hard constraints" />
          <StatCard label="Resumes" value={s?.resumes_generated ?? 0} accent="blue" loading={statsLoading} description="Generated" />
          <StatCard label="Applications" value={s?.applications_total ?? 0} accent="yellow" loading={statsLoading} description="All statuses" />
          <StatCard label="Pending Approval" value={s?.applications_pending_approval ?? 0} accent="red" loading={statsLoading} description="Awaiting your review" />
          <StatCard label="Submitted" value={s?.applications_submitted ?? 0} accent="green" loading={statsLoading} description="Sent to employers" />
          <StatCard label="Drafts" value={s?.applications_draft ?? 0} accent="gray" loading={statsLoading} description="In progress" />
        </div>
      </section>

      {/* Two-column section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Application funnel */}
        <section className="bg-gray-900 border border-gray-800 rounded-lg p-6" aria-labelledby="funnel-heading">
          <h2 id="funnel-heading" className="text-base font-semibold text-white mb-4">Application Funnel</h2>
          <div className="space-y-3">
            <MiniBar label="Discovered" value={s?.jobs_discovered ?? 0} max={Math.max(s?.jobs_discovered ?? 1, 1)} color="bg-blue-500" />
            <MiniBar label="Matched" value={s?.jobs_matched ?? 0} max={Math.max(s?.jobs_discovered ?? 1, 1)} color="bg-purple-500" />
            <MiniBar label="Eligible" value={s?.jobs_eligible ?? 0} max={Math.max(s?.jobs_discovered ?? 1, 1)} color="bg-green-500" />
            <MiniBar label="Applied" value={s?.applications_total ?? 0} max={Math.max(s?.jobs_eligible ?? 1, 1)} color="bg-yellow-500" />
            <MiniBar label="Submitted" value={s?.applications_submitted ?? 0} max={Math.max(s?.applications_total ?? 1, 1)} color="bg-emerald-500" />
          </div>
        </section>

        {/* Recent activity */}
        <section className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-lg p-6" aria-labelledby="activity-heading">
          <h2 id="activity-heading" className="text-base font-semibold text-white mb-4">Recent Activity</h2>
          <ActivityFeed items={activity} loading={activityLoading} />
        </section>
      </div>

      {/* Phase tracker */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-6" aria-labelledby="phases-heading">
        <h2 id="phases-heading" className="text-base font-semibold text-white mb-4">System Build Status</h2>
        <PhaseTracker />
      </section>

      {/* Quick links */}
      <nav aria-label="Quick navigation" className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/jobs", label: "Browse Jobs", desc: "Discover opportunities", icon: "🔍" },
          { href: "/profile", label: "My Profile", desc: "Manage evidence", icon: "👤" },
          { href: "/applications", label: "Applications", desc: "Track progress", icon: "📋" },
          { href: "/resumes", label: "Resumes", desc: "Generate tailored CVs", icon: "📄" },
        ].map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-600 transition-colors group focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label={link.label}
          >
            <div className="text-2xl mb-2" aria-hidden="true">{link.icon}</div>
            <p className="text-sm font-medium text-white group-hover:text-blue-400 transition-colors">{link.label}</p>
            <p className="text-xs text-gray-500 mt-0.5">{link.desc}</p>
          </a>
        ))}
      </nav>
    </div>
  );
}
