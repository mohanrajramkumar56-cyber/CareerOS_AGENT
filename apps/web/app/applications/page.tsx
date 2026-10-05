"use client";

/**
 * CareerOS — Applications Page (Phase 8)
 *
 * Displays job applications with state machine status and actions.
 */

import { useState, useEffect, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ApplicationResponse {
  id: string;
  candidate_id: string;
  job_id: string;
  resume_id: string | null;
  status: string;
  cover_letter: string | null;
  form_data: string | null;
  requires_approval: boolean;
  approved_by: string | null;
  approved_at: string | null;
  submitted_at: string | null;
  submission_method: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface ApplicationListResponse {
  applications: ApplicationResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchApplications(params: {
  page: number;
  page_size: number;
  status?: string;
}): Promise<ApplicationListResponse> {
  const qs = new URLSearchParams();
  qs.set("page", String(params.page));
  qs.set("page_size", String(params.page_size));
  if (params.status) qs.set("status", params.status);
  const res = await fetch(`${API_BASE}/api/v1/applications/?${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: "bg-gray-700 text-gray-400",
    pending_approval: "bg-yellow-500/20 text-yellow-400",
    approved: "bg-blue-500/20 text-blue-400",
    submitted: "bg-green-500/20 text-green-400",
    acknowledged: "bg-emerald-500/20 text-emerald-400",
    rejected: "bg-red-500/20 text-red-400",
    failed: "bg-orange-500/20 text-orange-400",
    withdrawn: "bg-gray-600/20 text-gray-500",
  };
  const label = status.replace(/_/g, " ");
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] ?? "bg-gray-700 text-gray-400"}`}>
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

// ── Application Card ──────────────────────────────────────────────────────────

function ApplicationCard({ app }: { app: ApplicationResponse }) {
  return (
    <article
      className="bg-gray-900 border border-gray-800 rounded-lg p-5 hover:border-gray-600 transition-colors"
      aria-labelledby={`app-${app.id}-title`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p id={`app-${app.id}-title`} className="text-sm font-mono text-gray-500">
            Application #{app.id.slice(0, 8)}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">Job: {app.job_id.slice(0, 8)}…</p>
        </div>
        <StatusBadge status={app.status} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        {app.submitted_at && (
          <div>
            <span className="text-gray-600">Submitted: </span>
            <span className="text-gray-400">{timeAgo(app.submitted_at)}</span>
          </div>
        )}
        {app.approved_at && (
          <div>
            <span className="text-gray-600">Approved: </span>
            <span className="text-gray-400">{timeAgo(app.approved_at)}</span>
          </div>
        )}
        {app.requires_approval && app.status === "draft" && (
          <div className="col-span-2">
            <span className="text-yellow-500/80 text-xs">⚠ Requires your approval before submission</span>
          </div>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between">
        <span className="text-xs text-gray-600">{timeAgo(app.created_at)}</span>
        {app.submission_method && (
          <span className="text-xs text-gray-600">via {app.submission_method}</span>
        )}
      </div>
    </article>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 animate-pulse">
      <div className="flex justify-between mb-3">
        <div className="h-3 bg-gray-800 rounded w-1/3" />
        <div className="h-5 bg-gray-800 rounded-full w-20" />
      </div>
      <div className="h-3 bg-gray-800 rounded w-2/3 mb-2" />
      <div className="h-3 bg-gray-800 rounded w-1/2" />
    </div>
  );
}

// ── Status summary bar ────────────────────────────────────────────────────────

const ALL_STATUSES = [
  "draft", "pending_approval", "approved", "submitted", "acknowledged", "rejected", "withdrawn",
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [data, setData] = useState<ApplicationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchApplications({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="p-8 space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Applications</h1>
          <p className="text-gray-400 mt-1">
            {data ? `${data.total} application${data.total !== 1 ? "s" : ""}` : "Loading…"}
          </p>
        </div>
      </header>

      {/* Status filter pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        <button
          onClick={() => { setStatusFilter(""); setPage(1); }}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${!statusFilter ? "bg-white text-gray-900 border-white" : "bg-transparent text-gray-400 border-gray-700 hover:border-gray-500"}`}
        >
          All
        </button>
        {ALL_STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${statusFilter === s ? "bg-white text-gray-900 border-white" : "bg-transparent text-gray-400 border-gray-700 hover:border-gray-500"}`}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="p-4 bg-red-500/10 border border-red-700 rounded text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && !error && data?.applications.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-500 text-lg">No applications yet</p>
          <p className="text-gray-600 text-sm mt-2">
            {statusFilter ? "Try a different status filter." : "Browse jobs and create your first application."}
          </p>
          {statusFilter && (
            <button onClick={() => { setStatusFilter(""); setPage(1); }} className="mt-4 text-sm text-blue-400 hover:text-blue-300 underline">
              Clear filter
            </button>
          )}
        </div>
      )}

      {!loading && !error && data && data.applications.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" role="list" aria-label="Applications">
            {data.applications.map((app) => (
              <div key={app.id} role="listitem"><ApplicationCard app={app} /></div>
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="flex items-center justify-between" aria-label="Pagination">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="px-4 py-2 text-sm rounded bg-gray-900 border border-gray-700 text-gray-300 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed">
                  Previous
                </button>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="px-4 py-2 text-sm rounded bg-gray-900 border border-gray-700 text-gray-300 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed">
                  Next
                </button>
              </div>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
