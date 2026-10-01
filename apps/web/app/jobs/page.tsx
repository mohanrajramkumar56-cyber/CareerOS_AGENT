import type { Metadata } from "next";

export const metadata: Metadata = { title: "Jobs — CareerOS" };

export default function JobsPage() {
  return (
    <div className="p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Jobs</h1>
        <p className="text-gray-400 mt-1">Discovered and matched jobs will appear here.</p>
      </header>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center">
        <p className="text-gray-500 text-lg">Job Intelligence</p>
        <p className="text-gray-600 text-sm mt-2">Phase 2 — coming next</p>
        <p className="text-gray-600 text-xs mt-1">
          API: <code className="text-gray-500">GET /api/v1/jobs</code>
        </p>
      </div>
    </div>
  );
}
