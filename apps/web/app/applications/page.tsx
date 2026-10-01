import type { Metadata } from "next";

export const metadata: Metadata = { title: "Applications — CareerOS" };

export default function ApplicationsPage() {
  return (
    <div className="p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Applications</h1>
        <p className="text-gray-400 mt-1">Track all job applications and their status.</p>
      </header>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center">
        <p className="text-gray-500 text-lg">Application Engine</p>
        <p className="text-gray-600 text-sm mt-2">Phase 5 — pending</p>
      </div>
    </div>
  );
}
