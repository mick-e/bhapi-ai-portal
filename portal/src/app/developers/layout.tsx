"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Code, LayoutDashboard, Webhook, BookOpen } from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

const navItems = [
  { href: "/developers", label: "Overview", icon: LayoutDashboard },
  { href: "/developers/dashboard", label: "API Dashboard", icon: Code },
  { href: "/developers/webhooks", label: "Webhooks", icon: Webhook },
  { href: "/developers/docs", label: "API Docs", icon: BookOpen },
];

export default function DevelopersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-8">
            <Link href="/">
              <BhapiLogo className="h-7 w-auto" />
            </Link>
            <nav className="hidden items-center gap-1 sm:flex">
              {navItems.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/developers" &&
                    pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary-50 text-primary-700"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <Link
            href="/dashboard"
            className="text-sm font-medium text-gray-500 hover:text-gray-900"
          >
            Back to Portal
          </Link>
        </div>
        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto px-4 pb-3 sm:hidden">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/developers" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-primary-50 text-primary-700"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main id="main-content" className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
