import { Suspense } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  description?: string;
  accent?: "blue" | "green" | "yellow" | "red" | "gray";
}

function StatCard({
  label,
  value,
  description,
  accent = "gray",
}: StatCardProps) {
  const accentColors = {
    blue: "border-l-blue-500",
    green: "border-l-green-500",
    yellow: "border-l-yellow-500",
    red: "border-l-red-500",
    gray: "border-l-gray-500",
  };

  return (
    <article
      className={`bg-gray-900 rounded-lg p-5 border border-gray-800 border-l-4 ${accentColors[accent]}`}
      aria-label={`${label}: ${value}`}
    >
      <p className="text-sm text-gray-400 font-medium uppercase tracking-wide">
        {label}
      </p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
      {description && (
        <p className="text-xs text-gray-500 mt-1">{description}</p>
      )}
    </article>
  );
}

function DashboardStats() {
  // Phase 0: Static placeholder connected to real data in Phase 1+
  return (
    <div
      className="grid grid-cols-2 lg:grid-cols-4 gap-4"
      aria-label="Dashboard statistics"
    >
      <StatCard
        label="Jobs Discovered"
        value="—"
        description="Phase 2 pending"
        accent="blue"
      />
      <StatCard
        label="Qualified Jobs"
        value="—"
        description="Phase 3 pending"
        accent="green"
      />
      <StatCard
        label="Applications"
        value="—"
        description="Phase 5 pending"
        accent="yellow"
      />
      <StatCard
        label="Pending Approvals"
        value="—"
        description="Phase 6 pending"
        accent="red"
      />
      <StatCard
        label="Interviews"
        value="—"
        description="Phase 7 pending"
        accent="green"
      />
      <StatCard
        label="Assessments"
        value="—"
        description="Phase 7 pending"
        accent="blue"
      />
      <StatCard
        label="Rejections"
        value="—"
        description="Phase 7 pending"
        accent="gray"
      />
      <StatCard
        label="Offers"
        value="—"
        description="Phase 7 pending"
        accent="green"
      />
    </div>
  );
}

function PhaseStatus() {
  const phases = [
    { name: "Phase 0: Foundation", status: "in-progress" },
    { name: "Phase 1: Candidate Intelligence", status: "pending" },
    { name: "Phase 2: Job Intelligence", status: "pending" },
    { name: "Phase 3: Matching Engine", status: "pending" },
    { name: "Phase 4: Resume Engine", status: "pending" },
    { name: "Phase 5: Application Engine", status: "pending" },
    { name: "Phase 6: Policy + Security", status: "pending" },
    { name: "Phase 7: Email + Follow-up", status: "pending" },
    { name: "Phase 8: Dashboard", status: "pending" },
    { name: "Phase 9: Observability", status: "pending" },
    { name: "Phase 10: Production Hardening", status: "pending" },
    { name: "Phase 11: End-to-End Validation", status: "pending" },
  ] as const;

  const statusColors = {
    complete: "bg-green-500/20 text-green-400 border-green-700",
    "in-progress": "bg-yellow-500/20 text-yellow-400 border-yellow-700",
    pending: "bg-gray-700/20 text-gray-400 border-gray-700",
  };

  return (
    <section aria-labelledby="phase-status-heading">
      <h2
        id="phase-status-heading"
        className="text-lg font-semibold text-white mb-3"
      >
        Build Progress
      </h2>
      <div className="space-y-2">
        {phases.map((phase) => (
          <div
            key={phase.name}
            className={`flex items-center justify-between px-4 py-2 rounded-lg border text-sm ${statusColors[phase.status]}`}
            role="status"
            aria-label={`${phase.name}: ${phase.status}`}
          >
            <span>{phase.name}</span>
            <span className="text-xs font-medium uppercase tracking-wide">
              {phase.status}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  return (
    <div className="p-8 space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">
          CareerOS — Autonomous AI Career Operating System
        </p>
      </header>

      <Suspense fallback={<p className="text-gray-400">Loading stats...</p>}>
        <DashboardStats />
      </Suspense>

      <PhaseStatus />
    </div>
  );
}
