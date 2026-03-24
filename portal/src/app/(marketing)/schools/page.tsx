"use client";

import Link from "next/link";
import {
  Monitor,
  BarChart3,
  GraduationCap,
  BookOpen,
  Shield,
  Users,
  Check,
  ArrowRight,
  Building2,
} from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-gray-600">{description}</p>
    </div>
  );
}

interface ComplianceBadgeProps {
  name: string;
  status: "certified" | "in-progress";
}

function ComplianceBadge({ name, status }: ComplianceBadgeProps) {
  const certified = status === "certified";
  return (
    <div
      className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ${
        certified
          ? "bg-teal-50 text-teal-800 ring-1 ring-teal-200"
          : "bg-gray-50 text-gray-500 ring-1 ring-gray-200"
      }`}
      aria-label={`${name} compliance badge — ${status}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${certified ? "bg-teal-500" : "bg-gray-300"}`}
        aria-hidden="true"
      />
      {name}
      {!certified && (
        <span className="ml-1 text-xs font-normal text-gray-400">
          (in progress)
        </span>
      )}
    </div>
  );
}

const FEATURES = [
  {
    icon: <Monitor className="h-6 w-6 text-teal-600" />,
    title: "Chrome Extension",
    description:
      "Monitor AI usage directly in the browser across all 10 major AI platforms. No proxy, no VPN — lightweight and CIPA-friendly.",
  },
  {
    icon: <GraduationCap className="h-6 w-6 text-teal-600" />,
    title: "SIS Sync",
    description:
      "Automatic roster sync with Clever and ClassLink OneRoster. Students and staff are provisioned the moment they appear in your SIS.",
  },
  {
    icon: <BarChart3 className="h-6 w-6 text-teal-600" />,
    title: "Compliance Dashboard",
    description:
      "One-click COPPA, FERPA, and GDPR reports ready for district administrators, school boards, and external auditors.",
  },
  {
    icon: <BookOpen className="h-6 w-6 text-teal-600" />,
    title: "Safeguarding Reports",
    description:
      "Automated eSafety reports with evidence trails. Raise concerns, track actions, and demonstrate duty of care.",
  },
  {
    icon: <Shield className="h-6 w-6 text-teal-600" />,
    title: "Policy Enforcement",
    description:
      "Apply school AI use policies at the extension level. Block platforms, restrict topics, and enforce academic integrity rules.",
  },
  {
    icon: <Users className="h-6 w-6 text-teal-600" />,
    title: "Teacher & Admin Roles",
    description:
      "Granular RBAC for teachers, department heads, and district admins. Teachers see their class; admins see the district.",
  },
];

const COMPLIANCE_BADGES: ComplianceBadgeProps[] = [
  { name: "COPPA 2026", status: "certified" },
  { name: "GDPR", status: "certified" },
  { name: "FERPA", status: "certified" },
  { name: "LGPD", status: "certified" },
  { name: "SOC 2 Type II", status: "in-progress" },
  { name: "ISO 27001", status: "in-progress" },
];

const VOLUME_TIERS = [
  {
    range: "1 – 499 students",
    price: "$4.00",
    detail: "per student / month",
    features: ["Full monitoring", "SIS sync", "Compliance reports", "Email support"],
  },
  {
    range: "500 – 2,499 students",
    price: "$3.00",
    detail: "per student / month",
    features: ["Everything in Starter", "Priority support", "Custom policies", "Admin training"],
    highlighted: true,
    badge: "Most Common",
  },
  {
    range: "2,500+ students",
    price: "Custom",
    detail: "contact us",
    features: [
      "Everything in Growth",
      "Dedicated CSM",
      "Custom integrations",
      "SLA guarantee",
      "On-site training",
    ],
  },
];

export default function SchoolsPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100">
        <div className="container-narrow flex h-16 items-center justify-between">
          <Link href="/">
            <BhapiLogo className="h-8 w-auto" />
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              Log in
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Request a Demo
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gradient-to-b from-teal-50 to-white py-20">
        <div className="container-narrow mx-auto max-w-3xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-teal-100 px-4 py-1.5">
            <Building2 className="h-4 w-4 text-teal-700" />
            <span className="text-sm font-semibold text-teal-700">
              Trusted by 340+ schools in 28 countries
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            District-wide AI safety,{" "}
            <span className="text-accent">built for educators</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-600">
            Deploy across your entire district in days. Integrates with Clever and
            ClassLink. Full COPPA 2026, FERPA, and GDPR compliance included —
            with reports your board will trust.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-teal-700"
            >
              Request a Demo
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Compliance Badges */}
      <section className="border-y border-gray-100 bg-gray-50 py-10">
        <div className="container-narrow">
          <p className="mb-6 text-center text-sm font-semibold uppercase tracking-widest text-gray-400">
            Compliance Certifications
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {COMPLIANCE_BADGES.map((badge) => (
              <ComplianceBadge key={badge.name} {...badge} />
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="container-narrow">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Built for how schools actually work
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              No IT overhead. No disruption to existing workflows. Just safety,
              compliance, and visibility — from day one.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <FeatureCard key={f.title} {...f} />
            ))}
          </div>
        </div>
      </section>

      {/* Per-seat Pricing */}
      <section className="bg-gray-50 py-20">
        <div className="container-narrow">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Per-seat pricing — transparent & scalable
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Pay only for active students. Volume discounts that scale with your
              district.
            </p>
          </div>
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-3">
            {VOLUME_TIERS.map((tier) => (
              <div
                key={tier.range}
                className={`relative flex flex-col rounded-2xl p-8 ${
                  tier.highlighted
                    ? "bg-primary-600 text-white shadow-xl ring-2 ring-primary-600"
                    : "bg-white shadow-sm ring-1 ring-gray-200"
                }`}
              >
                {tier.badge && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-accent px-4 py-1 text-xs font-bold uppercase tracking-wide text-white shadow">
                      {tier.badge}
                    </span>
                  </div>
                )}
                <p
                  className={`text-sm font-medium ${tier.highlighted ? "text-primary-200" : "text-gray-500"}`}
                >
                  {tier.range}
                </p>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    className={`text-4xl font-extrabold ${tier.highlighted ? "text-white" : "text-gray-900"}`}
                  >
                    {tier.price}
                  </span>
                </div>
                <p
                  className={`text-sm ${tier.highlighted ? "text-primary-100" : "text-gray-500"}`}
                >
                  {tier.detail}
                </p>
                <ul className="mt-6 flex-1 space-y-2.5">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check
                        className={`mt-0.5 h-4 w-4 flex-shrink-0 ${tier.highlighted ? "text-primary-200" : "text-teal-600"}`}
                      />
                      <span
                        className={tier.highlighted ? "text-primary-50" : "text-gray-700"}
                      >
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/contact"
                  className={`mt-8 block rounded-xl px-5 py-3 text-center text-sm font-bold transition-colors ${
                    tier.highlighted
                      ? "bg-white text-primary-700 hover:bg-primary-50"
                      : "bg-primary-600 text-white hover:bg-primary-700"
                  }`}
                >
                  Request a Demo
                </Link>
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-gray-500">
            Annual billing available. District-wide site licences available on
            request. All plans include a 30-day pilot.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-accent py-16">
        <div className="container-narrow text-center">
          <h2 className="text-3xl font-bold text-white">
            Ready to protect your students?
          </h2>
          <p className="mt-4 text-lg text-teal-100">
            Book a 30-minute demo. We&apos;ll walk through deployment for your
            district and answer every compliance question.
          </p>
          <Link
            href="/contact"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3 text-base font-bold text-teal-800 shadow-sm hover:bg-teal-50 transition-colors"
          >
            Request a Demo
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="container-narrow py-8 text-center text-sm text-gray-500">
          <p>&copy; {new Date().getFullYear()} Bhapi. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
