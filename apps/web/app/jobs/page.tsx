"use client";

/**
 * CareerOS — Jobs Page (Phase 2)
 *
 * Displays discovered jobs with search, filter, and pagination.
 * Fetches from GET /api/v1/jobs/ on mount.
 */

import { useState, useEffect, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface JobResponse {
  id: string;
  source: string;
  company: string;
  title: string;
  location: string | null;
  remote_type: string | null;
  employment_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  description: string | null;
  mandatory_skills: string | null;
  preferred_skills: string | null;
  freshness_status: string;
  posted_at: string | null;
  discovered_at: string;
  application_url: string | null;
  normalized: boolean;
}

interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJobs(params: {
  page: number;
  page_size: number;
  query?: string;
  remote_type?: string;
  employment_type?: string;
  freshness_status?: string;
}): Promise<JobListResponse> {
  const qs = new URLSearchParams();
  qs.set("page", String(params.page));
  qs.set("page_size", String(params.page_size));
  if (params.query) qs.set("query", params.query);
  if (params.remote_type) qs.set("remote_type", params.remote_type);
  if (params.employment_type) qs.set("employment_type", params.employment_type);
  if (params.freshness_status) qs.set("freshness_status", params.freshness_status);

  const res = await fetch(`${API_BASE}/api/v1/jobs/?${qs}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch jobs: ${res.status}`);
  return res.json();
}

function formatSalary(job: JobResponse): string | null {
  if (!job.salary_min && !job.salary_max) return null;
  const currency = job.salary_currency ?? "USD";
  const fmt = (n: number) =>
    n >= 1000 ? `${Math.round(n / 1000)}k` : String(n);
  if (job.salary_min && job.salary_max)
    return `${currency} ${fmt(job.salary_min)}–${fmt(job.salary_max)}`;
  if (job.salary_min) return `${currency} ${fmt(job.salary_min)}+`;
  return `${currency} up to ${fmt(job.salary_max!)}`;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

// ── Badge Components ──────────────────────────────────────────────────────────

function RemoteBadge({ type }: { type: string | null }) {
  if (!type || type === "unspecified") return null;
  const styles: Record<string, string> = {
    remote: "bg-green-500/20 text-green-400",
    hybrid: "bg-blue-500/20 text-blue-400",
    onsite: "bg-orange-500/20 text-orange-400",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[type] ?? "bg-gray-700 text-gray-400"}`}
    >
      {type.charAt(0).toUpperCase() + type.slice(1)}
    </span>
  );
}

function FreshnessBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-emerald-500/20 text-emerald-400",
    active: "bg-blue-500/20 text-blue-400",
    stale: "bg-yellow-500/20 text-yellow-400",
    expired: "bg-red-500/20 text-red-400",
    unknown: "bg-gray-700 text-gray-500",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] ?? styles.unknown}`}
    >
      {status}
    </span>
  );
}

function EmploymentBadge({ type }: { type: string | null }) {
  if (!type || type === "unspecified") return null;
  const label = type.replace(/_/g, " ");
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-400 font-medium">
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

// ── Skeleton Card ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 animate-pulse">
      <div className="h-4 bg-gray-800 rounded w-3/4 mb-3" />
      <div className="h-3 bg-gray-800 rounded w-1/2 mb-4" />
      <div className="flex gap-2 mb-4">
        <div className="h-5 bg-gray-800 rounded-full w-16" />
        <div className="h-5 bg-gray-800 rounded-full w-20" />
      </div>
      <div className="h-3 bg-gray-800 rounded w-full mb-2" />
      <div className="h-3 bg-gray-800 rounded w-4/5" />
    </div>
  );
}

// ── Job Card ──────────────────────────────────────────────────────────────────

function JobCard({ job }: { job: JobResponse }) {
  const salary = formatSalary(job);
  const mandatorySkills = job.mandatory_skills?.split(",").filter(Boolean) ?? [];

  return (
    <article
      className="bg-gray-900 border border-gray-800 rounded-lg p-5 hover:border-gray-600 transition-colors"
      aria-labelledby={`job-${job.id}-title`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3
            id={`job-${job.id}-title`}
            className="text-base font-semibold text-white truncate"
          >
            {job.title}
          </h3>
          <p className="text-sm text-gray-400 mt-0.5">{job.company}</p>
          {job.location && (
            <p className="text-xs text-gray-500 mt-0.5">{job.location}</p>
          )}
        </div>
        <FreshnessBadge status={job.freshness_status} />
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        <RemoteBadge type={job.remote_type} />
        <EmploymentBadge type={job.employment_type} />
        {salary && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 font-medium">
            {salary}
          </span>
        )}
      </div>

      {mandatorySkills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3" aria-label="Required skills">
          {mandatorySkills.slice(0, 6).map((skill) => (
            <span
              key={skill}
              className="text-xs px-2 py-0.5 bg-gray-800 text-gray-400 rounded border border-gray-700"
            >
              {skill}
            </span>
          ))}
          {mandatorySkills.length > 6 && (
            <span className="text-xs px-2 py-0.5 text-gray-600">
              +{mandatorySkills.length - 6} more
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-800">
        <span className="text-xs text-gray-600">
          {timeAgo(job.posted_at ?? job.discovered_at)}
        </span>
        <div className="flex gap-2">
          <button
            className="text-xs px-3 py-1.5 rounded bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-gray-600"
            aria-label={`View details for ${job.title} at ${job.company}`}
          >
            Details
          </button>
          {job.application_url && (
            <a
              href={job.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label={`Apply to ${job.title} at ${job.company}`}
            >
              Apply
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function JobsPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [remoteType, setRemoteType] = useState("");
  const [employmentType, setEmploymentType] = useState("");
  const [freshnessStatus, setFreshnessStatus] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJobs({
        page,
        page_size: PAGE_SIZE,
        query: query || undefined,
        remote_type: remoteType || undefined,
        employment_type: employmentType || undefined,
        freshness_status: freshnessStatus || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [page, query, remoteType, employmentType, freshnessStatus]);

  useEffect(() => {
    load();
  }, [load]);

  // Reset to page 1 when filters change
  const handleFilterChange = (setter: (v: string) => void) => (v: string) => {
    setter(v);
    setPage(1);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-bold text-white">Jobs</h1>
        <p className="text-gray-400 mt-1">
          {data
            ? `${data.total.toLocaleString()} job${data.total !== 1 ? "s" : ""} discovered`
            : "Discovering jobs..."}
        </p>
      </header>

      {/* Filters */}
      <div
        className="flex flex-wrap gap-3"
        role="search"
        aria-label="Filter jobs"
      >
        <input
          type="search"
          placeholder="Search title or company…"
          value={query}
          onChange={(e) => handleFilterChange(setQuery)(e.target.value)}
          className="flex-1 min-w-48 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Search jobs by title or company"
        />

        <select
          value={remoteType}
          onChange={(e) => handleFilterChange(setRemoteType)(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Filter by remote type"
        >
          <option value="">All locations</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">On-site</option>
        </select>

        <select
          value={employmentType}
          onChange={(e) => handleFilterChange(setEmploymentType)(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Filter by employment type"
        >
          <option value="">All types</option>
          <option value="full_time">Full Time</option>
          <option value="part_time">Part Time</option>
          <option value="contract">Contract</option>
          <option value="internship">Internship</option>
          <option value="freelance">Freelance</option>
        </select>

        <select
          value={freshnessStatus}
          onChange={(e) => handleFilterChange(setFreshnessStatus)(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Filter by freshness status"
        >
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="active">Active</option>
          <option value="stale">Stale</option>
          <option value="expired">Expired</option>
        </select>

        <button
          onClick={load}
          className="px-4 py-2 text-sm rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-gray-600"
          aria-label="Refresh job list"
        >
          Refresh
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div
          role="alert"
          className="p-4 bg-red-500/10 border border-red-700 rounded-lg text-red-400 text-sm"
        >
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
          aria-busy="true"
          aria-label="Loading jobs"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && data?.jobs.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-500 text-lg">No jobs found</p>
          <p className="text-gray-600 text-sm mt-2">
            {query || remoteType || employmentType || freshnessStatus
              ? "Try adjusting your filters."
              : "Jobs will appear here once the discovery pipeline runs."}
          </p>
          {(query || remoteType || employmentType || freshnessStatus) && (
            <button
              onClick={() => {
                setQuery("");
                setRemoteType("");
                setEmploymentType("");
                setFreshnessStatus("");
                setPage(1);
              }}
              className="mt-4 text-sm text-blue-400 hover:text-blue-300 underline"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Job grid */}
      {!loading && !error && data && data.jobs.length > 0 && (
        <div
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
          role="list"
          aria-label="Job listings"
        >
          {data.jobs.map((job) => (
            <div key={job.id} role="listitem">
              <JobCard job={job} />
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && data && totalPages > 1 && (
        <nav
          className="flex items-center justify-between pt-2"
          aria-label="Job list pagination"
        >
          <p className="text-sm text-gray-500">
            Page {page} of {totalPages} ({data.total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 text-sm rounded-lg bg-gray-900 border border-gray-700 text-gray-300 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-gray-600"
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 text-sm rounded-lg bg-gray-900 border border-gray-700 text-gray-300 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-gray-600"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </nav>
      )}
    </div>
  );
}
