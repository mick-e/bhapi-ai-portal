"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Activity,
  ShieldAlert,
  ShieldCheck,
  Bell,
  CreditCard,
  FileBarChart,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
  BarChart3,
  Plug,
} from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";
import { useAuth } from "@/hooks/use-auth";
import { useAlerts } from "@/hooks/use-alerts";
import { useTrialStatus } from "@/hooks/use-billing";

type AccountType = "family" | "school" | "club";

interface NavItem {
  href: string;
  label: string;
  icon: any; // Lucide icon component
  roles: AccountType[];
}

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["family", "school", "club"] },
  { href: "/members", label: "Children", icon: Users, roles: ["family"] },
  { href: "/members", label: "Students", icon: Users, roles: ["school"] },
  { href: "/members", label: "Members", icon: Users, roles: ["club"] },
  { href: "/activity", label: "Activity", icon: Activity, roles: ["family", "school", "club"] },
  { href: "/alerts", label: "Alerts", icon: Bell, roles: ["family", "school", "club"] },
  { href: "/classes", label: "Classes", icon: ShieldCheck, roles: ["school"] },
  { href: "/compliance", label: "Compliance", icon: ShieldAlert, roles: ["school"] },
  { href: "/spend", label: "Spend", icon: CreditCard, roles: ["family", "school"] },
  { href: "/analytics", label: "Analytics", icon: BarChart3, roles: ["family", "school", "club"] },
  { href: "/reports", label: "Reports", icon: FileBarChart, roles: ["family", "school", "club"] },
  { href: "/integrations", label: "Integrations", icon: Plug, roles: ["school"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["family", "school", "club"] },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const accountType = (user?.account_type || "family") as AccountType;
  const visibleItems = navItems.filter((item) => item.roles.includes(accountType));
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  // Fetch unread alert count for the notification badge
  const { data: alertsData } = useAlerts({ read: false, page_size: 1 });
  const unreadCount = alertsData?.total ?? 0;

  // Trial status
  const { data: trial } = useTrialStatus();
  const isLocked = trial?.is_locked ?? false;
  const isTrial = trial?.is_trial ?? false;
  const daysRemaining = trial?.days_remaining ?? 14;
  const showWarningBanner = isTrial && !isLocked && daysRemaining <= 3 && !bannerDismissed;

  // Redirect locked users to billing
  useEffect(() => {
    if (isLocked && pathname !== "/settings") {
      router.replace("/settings?tab=billing");
    }
  }, [isLocked, pathname, router]);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        aria-label="Main navigation"
        className={`
          fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white shadow-lg
          transform transition-transform duration-200 ease-in-out
          lg:static lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Sidebar header */}
        <div className="flex h-16 items-center justify-between border-b border-gray-100 px-6">
          <Link href="/dashboard" className="flex items-center gap-2">
            <BhapiLogo className="h-7 w-auto" />
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-400 hover:text-gray-600"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav aria-label="Sidebar navigation" className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {visibleItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <li key={`${item.href}-${item.label}`}>
                  <Link
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`
                      flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium
                      transition-colors
                      ${
                        isActive
                          ? "bg-primary-50 text-primary-700"
                          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                      }
                    `}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <span className="flex-1">{item.label}</span>
                    {item.href === "/alerts" && unreadCount > 0 && (
                      <span className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
                        {unreadCount > 99 ? "99+" : unreadCount}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Sidebar footer */}
        <div className="border-t border-gray-100 p-3">
          <button
            onClick={() => logout()}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 lg:px-8">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-gray-600 hover:text-gray-900"
            aria-label="Open navigation menu"
          >
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>

          <div className="hidden lg:block">
            <p className="text-sm text-gray-500">
              {user?.account_type
                ? `${user.account_type.charAt(0).toUpperCase() + user.account_type.slice(1)} account`
                : ""}
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Notifications */}
            <Link
              href="/alerts"
              className="relative rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
            >
              <Bell className="h-5 w-5" aria-hidden="true" />
              {unreadCount > 0 && (
                <span className="absolute right-1 top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Link>

            {/* Profile menu */}
            <div className="relative">
              <button
                onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
                aria-expanded={profileMenuOpen}
                aria-haspopup="true"
                aria-label="User menu"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary">
                  {user?.display_name?.charAt(0)?.toUpperCase() || "U"}
                </div>
                <span className="hidden text-sm font-medium text-gray-700 sm:block">
                  {user?.display_name || "User"}
                </span>
                <ChevronDown className="h-4 w-4 text-gray-400" />
              </button>

              {profileMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setProfileMenuOpen(false)}
                  />
                  <div className="absolute right-0 z-20 mt-2 w-56 rounded-lg bg-white py-1 shadow-lg ring-1 ring-gray-200">
                    <div className="border-b border-gray-100 px-4 py-3">
                      <p className="text-sm font-medium text-gray-900">
                        {user?.display_name || "User"}
                      </p>
                      <p className="text-xs text-gray-500">
                        {user?.email || ""}
                      </p>
                    </div>
                    <Link
                      href="/settings"
                      onClick={() => setProfileMenuOpen(false)}
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      Settings
                    </Link>
                    <button
                      onClick={() => {
                        setProfileMenuOpen(false);
                        logout();
                      }}
                      className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                    >
                      Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Trial banners */}
        {isLocked && (
          <div className="bg-red-600 px-4 py-3 text-center text-sm font-medium text-white">
            Your free trial has expired. Safety monitoring is paused.{" "}
            <Link href="/settings?tab=billing" className="underline font-bold">
              Subscribe now
            </Link>{" "}
            or email{" "}
            <a href="mailto:contactus@bhapi.io" className="underline font-bold">
              contactus@bhapi.io
            </a>
          </div>
        )}
        {showWarningBanner && (
          <div className="bg-amber-500 px-4 py-2.5 text-center text-sm font-medium text-white flex items-center justify-center gap-2">
            <span>
              Your trial ends in {daysRemaining} day{daysRemaining !== 1 ? "s" : ""}.{" "}
              <Link href="/settings?tab=billing" className="underline font-bold">
                Subscribe now
              </Link>
            </span>
            <button
              onClick={() => setBannerDismissed(true)}
              className="ml-2 rounded p-0.5 hover:bg-amber-600"
              aria-label="Dismiss trial banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Page content */}
        <main id="main-content" className="flex-1 overflow-y-auto p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
