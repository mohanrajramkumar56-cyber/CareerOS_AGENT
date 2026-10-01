import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "CareerOS — Autonomous AI Career Platform",
  description: "CareerOS: AI-powered career operating system",
};

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/applications", label: "Applications" },
  { href: "/profile", label: "Profile" },
  { href: "/resumes", label: "Resumes" },
  { href: "/approvals", label: "Approvals" },
  { href: "/policies", label: "Policies" },
  { href: "/audit", label: "Audit" },
  { href: "/health", label: "Health" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} antialiased bg-gray-950 text-gray-100 font-sans`}
      >
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside
            className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col"
            aria-label="Main navigation"
          >
            <div className="p-6 border-b border-gray-800">
              <h1 className="text-xl font-bold text-white">CareerOS</h1>
              <p className="text-xs text-gray-400 mt-1">
                Autonomous Career Platform
              </p>
            </div>
            <nav className="flex-1 p-4" aria-label="Site navigation">
              <ul className="space-y-1" role="list">
                {navLinks.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="block px-4 py-2 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            <div className="p-4 border-t border-gray-800">
              <p className="text-xs text-gray-500">v0.1.0 — Phase 0</p>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 flex flex-col overflow-auto" role="main">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
