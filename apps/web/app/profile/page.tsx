/**
 * CareerOS — Candidate Profile Page
 *
 * Shows the candidate's profile, skills, experience, evidence facts.
 * In Phase 1 this is a skeleton that renders real API data when authenticated.
 * Auth/session management is Phase 6 — for now shows structure + placeholder.
 */

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Profile — CareerOS",
};

interface SectionProps {
  title: string;
  children: React.ReactNode;
  badge?: string;
  badgeColor?: "green" | "yellow" | "red" | "gray" | "blue";
}

function Section({ title, children, badge, badgeColor = "gray" }: SectionProps) {
  const colors = {
    green: "bg-green-500/20 text-green-400",
    yellow: "bg-yellow-500/20 text-yellow-400",
    red: "bg-red-500/20 text-red-400",
    gray: "bg-gray-700 text-gray-400",
    blue: "bg-blue-500/20 text-blue-400",
  };
  return (
    <section
      className="bg-gray-900 rounded-lg border border-gray-800 p-6"
      aria-labelledby={`section-${title.replace(/\s+/g, "-").toLowerCase()}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          id={`section-${title.replace(/\s+/g, "-").toLowerCase()}`}
          className="text-lg font-semibold text-white"
        >
          {title}
        </h2>
        {badge && (
          <span
            className={`text-xs px-2 py-1 rounded-full font-medium ${colors[badgeColor]}`}
          >
            {badge}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

interface FieldProps {
  label: string;
  value: string | number | null | undefined;
  placeholder?: string;
}

function Field({ label, value, placeholder = "Not set" }: FieldProps) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wide font-medium">
        {label}
      </dt>
      <dd className={`mt-1 text-sm ${value ? "text-gray-200" : "text-gray-600 italic"}`}>
        {value ?? placeholder}
      </dd>
    </div>
  );
}

interface EvidenceBadgeProps {
  strength: string;
}

function EvidenceBadge({ strength }: EvidenceBadgeProps) {
  const styles: Record<string, string> = {
    verified: "bg-green-500/20 text-green-400 border-green-700",
    strong: "bg-blue-500/20 text-blue-400 border-blue-700",
    moderate: "bg-yellow-500/20 text-yellow-400 border-yellow-700",
    weak: "bg-orange-500/20 text-orange-400 border-orange-700",
    unknown: "bg-gray-700/40 text-gray-500 border-gray-600",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border font-medium ${styles[strength] ?? styles.unknown}`}
      aria-label={`Evidence strength: ${strength}`}
    >
      {strength}
    </span>
  );
}

// ── Placeholder data (replaced by real API data in Phase 6 with auth) ────────

const PLACEHOLDER_PROFILE = {
  full_name: "Your Name",
  headline: "Your Professional Headline",
  current_city: null,
  current_country: null,
  years_of_experience: null,
  preferred_remote_type: null,
  work_authorization: null,
};

const PLACEHOLDER_SKILLS = [
  { name: "Python", strength: "verified" },
  { name: "FastAPI", strength: "strong" },
  { name: "PostgreSQL", strength: "moderate" },
  { name: "Docker", strength: "weak" },
  { name: "Kubernetes", strength: "unknown" },
];

const PLACEHOLDER_FACTS = [
  {
    category: "experience",
    claim: "Led backend engineering team at Acme Corp",
    evidence_strength: "strong",
  },
  {
    category: "certification",
    claim: "AWS Certified Solutions Architect",
    evidence_strength: "verified",
  },
  {
    category: "skill",
    claim: "Machine learning with PyTorch",
    evidence_strength: "unknown",
  },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const profile = PLACEHOLDER_PROFILE;

  return (
    <div className="p-8 space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{profile.full_name}</h1>
          <p className="text-gray-400 mt-1">{profile.headline}</p>
        </div>
        <div className="flex gap-2">
          <button
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Edit candidate profile"
          >
            Edit Profile
          </button>
        </div>
      </header>

      {/* Identity */}
      <Section title="Identity" badge="Phase 1" badgeColor="blue">
        <dl className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="Location" value={
            [profile.current_city, profile.current_country].filter(Boolean).join(", ") || null
          } />
          <Field label="Experience" value={
            profile.years_of_experience ? `${profile.years_of_experience} years` : null
          } />
          <Field label="Work Style" value={profile.preferred_remote_type} />
          <Field label="Authorization" value={profile.work_authorization} />
        </dl>
      </Section>

      {/* Skills with evidence strength */}
      <Section title="Skills" badge={`${PLACEHOLDER_SKILLS.length} skills`}>
        <div
          className="flex flex-wrap gap-2"
          role="list"
          aria-label="Candidate skills"
        >
          {PLACEHOLDER_SKILLS.map((skill) => (
            <div
              key={skill.name}
              role="listitem"
              className="flex items-center gap-2 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700"
            >
              <span className="text-sm text-gray-200">{skill.name}</span>
              <EvidenceBadge strength={skill.strength} />
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Evidence strength shows how well each skill is backed by verifiable evidence.
          Skills marked <strong className="text-gray-400">unknown</strong> cannot be used in applications.
        </p>
      </Section>

      {/* Evidence Facts */}
      <Section
        title="Evidence Graph"
        badge={`${PLACEHOLDER_FACTS.length} facts`}
        badgeColor="blue"
      >
        <div className="space-y-3" role="list" aria-label="Candidate facts">
          {PLACEHOLDER_FACTS.map((fact, i) => (
            <div
              key={i}
              role="listitem"
              className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700"
            >
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wide mr-2">
                  {fact.category}
                </span>
                <span className="text-sm text-gray-200">{fact.claim}</span>
              </div>
              <EvidenceBadge strength={fact.evidence_strength} />
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-700 rounded-lg">
          <p className="text-xs text-yellow-400">
            <strong>Truth policy:</strong> Facts with{" "}
            <EvidenceBadge strength="unknown" /> evidence will never be
            included in your resume or auto-filled in applications.
          </p>
        </div>
      </Section>

      {/* API status note */}
      <div className="text-xs text-gray-600 text-center py-2">
        Profile page connected to{" "}
        <code className="text-gray-500">GET /api/v1/candidates/profile</code> —
        Authentication UI ships in Phase 6.
      </div>
    </div>
  );
}
