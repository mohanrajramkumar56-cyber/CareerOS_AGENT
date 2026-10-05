"use client";

/**
 * CareerOS — Resumes Page (Phase 8)
 *
 * Lists generated resumes, allows generating new ones.
 */

import { useState, useEffect, useCallback } from "react";

interface ResumeSummary {
  id: string;
  candidate_id: string;
  job_id: string | null;
  title: string;
  template: string;
  is_tailored: boolean;
  truth_policy_enforced: boolean;
  facts_excluded_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

interface ResumeListResponse {
  resumes: ResumeSummary[];
  total: number;
  page: number;
  page_size: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchResumes(page = 1, page_size = 20): Promise<ResumeListResponse> {
  const res = await fetch(`${API_BASE}/api/v1/resumes/?page=${page}&page_size=${page_size}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

const TEMPLATE_COLORS: Record<string, string> = {
  standard: "text-blue-400 bg-blue-500/10",
  minimal: "text-gray-400 bg-gray-700/30",
  technical: "text-purple-400 bg-purple-500/10",
  executive: "text-yellow-400 bg-yellow-500/10",
};

function ResumeCard({ resume }: { resume: ResumeSummary }) {
  return (
    <article
      className="bg-gray-900 border border-gray-800 rounded-lg p-5 hover:border-gray-600 transition-colors"
      aria-labelledby={`resume-${resume.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 id={`resume-${resume.id}`} className="text-sm font-medium text-white truncate flex-1">
          {resume.title}
        </h3>
        {resume.is_tailored && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 flex-shrink-0">Tailored</span>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mt-2">
        <span className={`text-xs px-2 py-0.5 rounded font-medium ${TEMPLATE_COLORS[resume.template] ?? "text-gray-400 bg-gray-700"}`}>
          {resume.template}
        </span>
        {resume.truth_policy_enforced && (
          <span className="text-xs px-2 py-0.5 rounded bg-green-500/10 text-green-400">Truth Policy ✓</span>
        )}
        {resume.facts_excluded_count > 0 && (
          <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500">
            {resume.facts_excluded_count} fact{resume.facts_excluded_count !== 1 ? "s" : ""} excluded
          </span>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between">
        <span className="text-xs text-gray-600">{timeAgo(resume.created_at)}</span>
        <div className="flex gap-2">
          <a
            href={`${API_BASE}/api/v1/resumes/${resume.id}/markdown`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
            aria-label={`View markdown for ${resume.title}`}
          >
            Markdown
          </a>
        </div>
      </div>
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 animate-pulse">
      <div className="h-4 bg-gray-800 rounded w-3/4 mb-3" />
      <div className="flex gap-2 mb-4">
        <div className="h-5 bg-gray-800 rounded w-16" />
        <div className="h-5 bg-gray-800 rounded w-24" />
      </div>
      <div className="h-3 bg-gray-800 rounded w-1/3" />
    </div>
  );
}

export default function ResumesPage() {
  const [data, setData] = useState<ResumeListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchResumes(page));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load resumes");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="p-8 space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Resumes</h1>
          <p className="text-gray-400 mt-1">
            {data ? `${data.total} resume${data.total !== 1 ? "s" : ""} generated` : "Loading…"}
          </p>
        </div>
        <p className="text-xs text-gray-600 mt-1">
          Generate via <code className="text-gray-500">POST /api/v1/resumes/</code>
        </p>
      </header>

      {error && (
        <div role="alert" className="p-4 bg-red-500/10 border border-red-700 rounded text-red-400 text-sm">{error}</div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && !error && data?.resumes.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-500 text-lg">No resumes yet</p>
          <p className="text-gray-600 text-sm mt-2">
            Use <code className="text-gray-500">POST /api/v1/resumes/</code> to generate your first evidence-backed resume.
          </p>
          <div className="mt-6 p-4 bg-gray-800 rounded text-left text-xs text-gray-400 font-mono max-w-sm mx-auto">
            {`{ "template": "standard", "job_id": "optional-uuid" }`}
          </div>
        </div>
      )}

      {!loading && !error && data && data.resumes.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" role="list">
            {data.resumes.map((r) => (
              <div key={r.id} role="listitem"><ResumeCard resume={r} /></div>
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
