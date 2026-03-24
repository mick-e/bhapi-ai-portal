"use client";

import Link from "next/link";
import {
  Handshake,
  DollarSign,
  Shield,
  Users,
  Star,
  CheckCircle,
  ArrowRight,
  Award,
  HeadphonesIcon,
  BookOpen,
  TrendingUp,
  Globe,
  BadgeCheck,
} from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

const tiers = [
  {
    name: "Referral",
    badge: "Free to join",
    commission: "10%",
    description:
      "Refer schools or families to Bhapi and earn a recurring commission for the life of the customer.",
    requirements: "No approval needed — sign up and start referring.",
    benefits: [
      "10% recurring revenue share",
      "Unique referral link + tracking dashboard",
      "Co-branded one-pager (PDF)",
      "Monthly commission payments via Wise",
      "Partner newsletter with product updates",
    ],
    cta: "Join for Free",
    highlighted: false,
  },
  {
    name: "Reseller",
    badge: "Most Popular",
    commission: "15%",
    description:
      "Purchase and resell Bhapi subscriptions directly to schools and districts. Higher margin, full control.",
    requirements: "Application required — approved within 5 business days.",
    benefits: [
      "15% recurring revenue share",
      "White-label co-branded portal",
      "Partner dashboard with real-time analytics",
      "Priority email and Slack support",
      "Full compliance documentation package",
      "Quarterly business reviews",
      "Early access to new features",
    ],
    cta: "Apply Now",
    highlighted: true,
  },
  {
    name: "Strategic",
    badge: "Enterprise",
    commission: "Custom",
    description:
      "Deep integration for national distributors, EdTech platforms, and managed service providers.",
    requirements: "Contact our partnerships team to discuss terms.",
    benefits: [
      "Custom revenue share negotiated",
      "API integration and white-label options",
      "Dedicated partner success manager",
      "Co-marketing budget and joint campaigns",
      "Custom onboarding and training program",
      "SLA-backed support with escalation path",
      "Influence on product roadmap",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

const benefits = [
  {
    icon: DollarSign,
    title: "Recurring Revenue",
    description:
      "Earn 15% of every subscription payment for the full lifetime of each customer you bring on board.",
  },
  {
    icon: BookOpen,
    title: "Co-Branded Materials",
    description:
      "Ready-made sales decks, one-pagers, and ROI calculators tailored for school decision-makers.",
  },
  {
    icon: TrendingUp,
    title: "Partner Dashboard",
    description:
      "Real-time visibility into your referrals, conversion rates, and commission earnings.",
  },
  {
    icon: HeadphonesIcon,
    title: "Priority Support",
    description:
      "Dedicated partner support channel with guaranteed 4-hour response time on business days.",
  },
  {
    icon: Shield,
    title: "Compliance Package",
    description:
      "Full COPPA, GDPR, and state-level compliance documentation to help close deals faster.",
  },
  {
    icon: Globe,
    title: "Deployment Guides",
    description:
      "Step-by-step technical guides for Chrome extension rollout, SSO setup, and SIS sync.",
  },
];

const complianceBadges = [
  {
    icon: BadgeCheck,
    label: "COPPA 2026 Compliant",
    color: "text-green-700",
    bg: "bg-green-50",
    border: "border-green-200",
  },
  {
    icon: BadgeCheck,
    label: "GDPR Ready",
    color: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
  {
    icon: BadgeCheck,
    label: "FERPA Aligned",
    color: "text-purple-700",
    bg: "bg-purple-50",
    border: "border-purple-200",
  },
  {
    icon: Award,
    label: "SOC 2 (In Progress)",
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-200",
  },
];

const steps = [
  { step: "01", title: "Apply", description: "Complete the short partner application form." },
  { step: "02", title: "Approved", description: "Our team reviews and approves within 5 business days." },
  { step: "03", title: "Training", description: "Complete a 60-minute onboarding session and get your materials." },
  { step: "04", title: "Go Live", description: "Start referring or reselling and track earnings in your dashboard." },
];

export default function PartnersPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <BhapiLogo className="h-8 w-auto" />
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Log in
            </Link>
            <Link
              href="#apply"
              className="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors"
              style={{ backgroundColor: "#FF6B35" }}
            >
              Apply to Partner
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-20 sm:py-28" style={{ background: "linear-gradient(135deg, #fff7f3 0%, #f0fdfa 100%)" }}>
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <div
            className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium mb-6"
            style={{ backgroundColor: "#fff3ee", color: "#FF6B35" }}
          >
            <Handshake className="h-4 w-4" />
            Channel Partnership Program
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
            Partner with{" "}
            <span style={{ color: "#FF6B35" }}>Bhapi</span>
          </h1>
          <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
            Bring AI safety to your schools and communities — and earn recurring revenue for every family or school you onboard.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="#apply"
              className="inline-flex items-center justify-center gap-2 rounded-lg px-6 py-3 text-base font-semibold text-white transition-colors"
              style={{ backgroundColor: "#FF6B35" }}
            >
              Apply to Partner
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/roi-calculator"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              ROI Calculator
            </Link>
          </div>
          <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-gray-500">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-green-500" />
              15% recurring commission
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Paid monthly via Wise
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Full compliance docs included
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">How it works</h2>
            <p className="mt-3 text-lg text-gray-600">From application to first commission in under 2 weeks.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((s) => (
              <div key={s.step} className="text-center">
                <div
                  className="inline-flex h-12 w-12 items-center justify-center rounded-full text-lg font-bold text-white mb-4"
                  style={{ backgroundColor: "#FF6B35" }}
                >
                  {s.step}
                </div>
                <h3 className="text-lg font-semibold text-gray-900">{s.title}</h3>
                <p className="mt-1 text-sm text-gray-600">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tiers */}
      <section className="py-20 bg-gray-50" id="tiers">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Partnership Tiers</h2>
            <p className="mt-3 text-lg text-gray-600">Choose the level that fits your business model.</p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-2xl border p-8 flex flex-col ${
                  tier.highlighted
                    ? "border-2 shadow-xl relative"
                    : "border-gray-200 bg-white"
                }`}
                style={
                  tier.highlighted
                    ? { borderColor: "#FF6B35", backgroundColor: "#fff7f3" }
                    : {}
                }
              >
                {tier.highlighted && (
                  <div
                    className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-xs font-semibold text-white"
                    style={{ backgroundColor: "#FF6B35" }}
                  >
                    {tier.badge}
                  </div>
                )}
                {!tier.highlighted && (
                  <span className="inline-block rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 mb-2 self-start">
                    {tier.badge}
                  </span>
                )}
                <h3 className="text-2xl font-bold text-gray-900">{tier.name}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    className="text-4xl font-extrabold"
                    style={{ color: "#FF6B35" }}
                  >
                    {tier.commission}
                  </span>
                  {tier.commission !== "Custom" && (
                    <span className="text-gray-500 text-sm">recurring revenue</span>
                  )}
                </div>
                <p className="mt-4 text-sm text-gray-600">{tier.description}</p>
                <p className="mt-2 text-xs text-gray-400 italic">{tier.requirements}</p>
                <ul className="mt-6 space-y-3 flex-1">
                  {tier.benefits.map((b) => (
                    <li key={b} className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle
                        className="h-4 w-4 mt-0.5 flex-shrink-0"
                        style={{ color: "#0D9488" }}
                      />
                      {b}
                    </li>
                  ))}
                </ul>
                <Link
                  href="#apply"
                  className="mt-8 inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors"
                  style={
                    tier.highlighted
                      ? { backgroundColor: "#FF6B35", color: "#fff" }
                      : { backgroundColor: "#f3f4f6", color: "#374151" }
                  }
                >
                  {tier.cta}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Everything you need to sell Bhapi</h2>
            <p className="mt-3 text-lg text-gray-600">
              We equip our partners with the tools, collateral, and support to close deals confidently.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {benefits.map((b) => {
              const Icon = b.icon;
              return (
                <div key={b.title} className="rounded-xl border border-gray-200 p-6">
                  <div
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg mb-4"
                    style={{ backgroundColor: "#fff3ee" }}
                  >
                    <Icon className="h-5 w-5" style={{ color: "#FF6B35" }} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">{b.title}</h3>
                  <p className="mt-2 text-sm text-gray-600">{b.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Commission details */}
      <section className="py-20" style={{ backgroundColor: "#f0fdfa" }}>
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-2xl bg-white border border-teal-100 shadow-sm p-10">
            <div className="flex items-center gap-3 mb-6">
              <div
                className="inline-flex h-10 w-10 items-center justify-center rounded-lg"
                style={{ backgroundColor: "#f0fdfa" }}
              >
                <DollarSign className="h-5 w-5" style={{ color: "#0D9488" }} />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Commission Structure</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
              <div className="rounded-xl bg-gray-50 p-5 text-center">
                <p className="text-sm font-medium text-gray-500 mb-1">Referral Partners</p>
                <p className="text-3xl font-extrabold" style={{ color: "#FF6B35" }}>10%</p>
                <p className="text-xs text-gray-400 mt-1">of MRR, for life of customer</p>
              </div>
              <div className="rounded-xl p-5 text-center border-2" style={{ borderColor: "#FF6B35", backgroundColor: "#fff7f3" }}>
                <p className="text-sm font-medium text-gray-500 mb-1">Reseller Partners</p>
                <p className="text-3xl font-extrabold" style={{ color: "#FF6B35" }}>15%</p>
                <p className="text-xs text-gray-400 mt-1">of MRR, for life of customer</p>
              </div>
              <div className="rounded-xl bg-gray-50 p-5 text-center">
                <p className="text-sm font-medium text-gray-500 mb-1">Strategic Partners</p>
                <p className="text-3xl font-extrabold text-gray-700">Custom</p>
                <p className="text-xs text-gray-400 mt-1">negotiated rate + bonuses</p>
              </div>
            </div>
            <ul className="space-y-3 text-sm text-gray-700">
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-teal-600" />
                Commissions paid monthly on the 1st via Wise (bank transfer, no PayPal fees)
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-teal-600" />
                60-day cookie window — customers referred through your link are attributed to you
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-teal-600" />
                Commissions are recurring — you earn every month the customer stays subscribed
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-teal-600" />
                Minimum payout threshold: $50 USD (unpaid balance rolls to next month)
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-teal-600" />
                Full earnings history visible in your partner dashboard in real time
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Compliance badges */}
      <section className="py-16 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900">Built for regulated environments</h2>
            <p className="mt-2 text-gray-600">
              Bhapi is purpose-built for schools and families — compliance is a feature, not an afterthought.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-4">
            {complianceBadges.map((badge) => {
              const Icon = badge.icon;
              return (
                <div
                  key={badge.label}
                  className={`flex items-center gap-2 rounded-full border px-5 py-2.5 text-sm font-medium ${badge.bg} ${badge.border} ${badge.color}`}
                >
                  <Icon className="h-4 w-4" />
                  {badge.label}
                </div>
              );
            })}
          </div>
          <p className="mt-6 text-center text-xs text-gray-400">
            Full compliance documentation available to Reseller and Strategic partners on request.
          </p>
        </div>
      </section>

      {/* Target markets */}
      <section className="py-16 bg-gray-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900">Who do our partners sell to?</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="rounded-xl bg-white border border-gray-200 p-6">
              <Users className="h-8 w-8 mb-3" style={{ color: "#FF6B35" }} />
              <h3 className="font-semibold text-gray-900 mb-2">K-12 Schools</h3>
              <p className="text-sm text-gray-600">
                District IT directors, school principals, and safeguarding leads who need AI governance tools that comply with COPPA and state mandates.
              </p>
            </div>
            <div className="rounded-xl bg-white border border-gray-200 p-6">
              <Star className="h-8 w-8 mb-3" style={{ color: "#0D9488" }} />
              <h3 className="font-semibold text-gray-900 mb-2">Youth Organizations</h3>
              <p className="text-sm text-gray-600">
                Sports clubs, after-school programs, and community organizations that supervise children using AI tools.
              </p>
            </div>
            <div className="rounded-xl bg-white border border-gray-200 p-6">
              <Shield className="h-8 w-8 mb-3" style={{ color: "#FF6B35" }} />
              <h3 className="font-semibold text-gray-900 mb-2">MSPs & EdTech Resellers</h3>
              <p className="text-sm text-gray-600">
                Managed service providers and EdTech distributors who bundle Bhapi with their existing school technology stack.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA / Apply */}
      <section className="py-20" id="apply" style={{ background: "linear-gradient(135deg, #FF6B35 0%, #e85d2a 100%)" }}>
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 text-center text-white">
          <Handshake className="h-12 w-12 mx-auto mb-6 opacity-90" />
          <h2 className="text-3xl font-bold">Ready to partner with Bhapi?</h2>
          <p className="mt-4 text-lg opacity-90">
            Join our partner program and start earning recurring revenue while helping schools and families stay safe in the age of AI.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="mailto:partners@bhapi.ai?subject=Partner Program Application"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-base font-semibold transition-colors hover:bg-gray-50"
              style={{ color: "#FF6B35" }}
            >
              Apply to Partner
              <ArrowRight className="h-4 w-4" />
            </a>
            <Link
              href="/roi-calculator"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/40 bg-white/10 px-6 py-3 text-base font-semibold text-white hover:bg-white/20 transition-colors"
            >
              View ROI Calculator
            </Link>
          </div>
          <p className="mt-6 text-sm opacity-75">
            Questions? Email{" "}
            <a href="mailto:partners@bhapi.ai" className="underline">
              partners@bhapi.ai
            </a>{" "}
            — we respond within 1 business day.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-10 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <BhapiLogo className="h-6 w-auto" />
          <div className="flex gap-6 text-sm text-gray-500">
            <Link href="/legal/privacy" className="hover:text-gray-900">Privacy</Link>
            <Link href="/legal/terms" className="hover:text-gray-900">Terms</Link>
            <Link href="/roi-calculator" className="hover:text-gray-900">ROI Calculator</Link>
            <a href="mailto:partners@bhapi.ai" className="hover:text-gray-900">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
