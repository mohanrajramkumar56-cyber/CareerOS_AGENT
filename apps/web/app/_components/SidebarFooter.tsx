"use client";

/**
 * SidebarFooter — Client component for auth-aware sidebar footer.
 *
 * Shows:
 *  - When loading: a subtle placeholder
 *  - When authenticated: user email + logout button
 *  - When unauthenticated: Login and Register links
 */

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

export function SidebarFooter() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="p-4 border-t border-gray-800">
        <div className="h-4 w-32 bg-gray-800 rounded animate-pulse" />
      </div>
    );
  }

  if (user) {
    return (
      <div className="p-4 border-t border-gray-800 space-y-2">
        {/* User info */}
        <div className="flex items-center gap-2 min-w-0">
          {/* Avatar initial */}
          <div
            className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-semibold text-white select-none"
            aria-hidden="true"
          >
            {(user.full_name ?? user.email).charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            {user.full_name && (
              <p className="text-xs font-medium text-gray-200 truncate">
                {user.full_name}
              </p>
            )}
            <p className="text-xs text-gray-400 truncate" title={user.email}>
              {user.email}
            </p>
          </div>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-1.5 text-xs text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Sign out
        </button>
      </div>
    );
  }

  // Not authenticated
  return (
    <div className="p-4 border-t border-gray-800 space-y-1">
      <Link
        href="/login"
        className="block px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        Sign in
      </Link>
      <Link
        href="/register"
        className="block px-3 py-2 text-sm text-blue-400 hover:bg-gray-800 hover:text-blue-300 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        Create account
      </Link>
    </div>
  );
}
