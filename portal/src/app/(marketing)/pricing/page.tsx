"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, X, ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

// --- Types ---

interface TierValue {
  value: string | boolean | null;
  note?: string;
}

interface FeatureRow {
  label: string;
  free: TierValue;
  family: TierValue;
  familyPlus: TierValue;
  school: TierValue;
  enterprise: TierValue;
}

interface FaqItem {
  question: string;
  answer: string;
}

// --- Data ---

const FEATURE_ROWS: FeatureRow[] = [
  {
    label: "Children / Students",
    free: { value: "1" },
    family: { value: "3" },
    familyPlus: { value: "5" },
    school: { value: "Unlimited" },
    enterprise: { value: "Unlimited" },
  },
  {
    label: "AI monitoring",
    free: { value: true, note: "3 platforms" },
    family: { value: true, note: "10 platforms" },
    familyPlus: { value: true, note: "10 platforms" },
    school: { value: true, note: "10 platforms" },
    enterprise: { value: true, note: "Custom" },
  },
  {
    label: "Safe social network",
    free: { value: false },
    family: { value: true },
    familyPlus: { value: true },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "Screen time controls",
    free: { value: false },
    family: { value: true },
    familyPlus: { value: true },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "Location tracking",
    free: { value: false },
    family: { value: true },
    familyPlus: { value: true },
    school: { value: false },
    enterprise: { value: true },
  },
  {
    label: "Creative AI tools",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: true },
    school: { value: false },
    enterprise: { value: true },
  },
  {
    label: "Priority support",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: true },
    school: { value: true },
    enterprise: { value: true, note: "Dedicated CSM" },
  },
  {
    label: "SIS integration",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: false },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "Custom compliance reports",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: false },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "Activity history",
    free: { value: "7 days" },
    family: { value: "90 days" },
    familyPlus: { value: "Unlimited" },
    school: { value: "1 year" },
    enterprise: { value: "Custom" },
  },
  {
    label: "Chrome extension",
    free: { value: true },
    family: { value: true },
    familyPlus: { value: true },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "SSO / SAML",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: false },
    school: { value: true },
    enterprise: { value: true },
  },
  {
    label: "Custom AI policies",
    free: { value: false },
    family: { value: false },
    familyPlus: { value: false },
    school: { value: true },
    enterprise: { value: true },
  },
];

const FAQS: FaqItem[] = [
  {
    question: "Is there a free trial?",
    answer:
      "Yes. All paid plans include a 14-day free trial. No credit card is required to start. Schools get a 30-day pilot with full features.",
  },
  {
    question: "Can I switch plans at any time?",
    answer:
      "Absolutely. You can upgrade or downgrade your plan at any time from the billing settings. Changes take effect at the start of your next billing cycle. Upgrades take effect immediately.",
  },
  {
    question: "How is school per-seat pricing calculated?",
    answer:
      "School pricing is based on the number of active students at the time of billing. Students who haven't signed in for 30 days are automatically marked inactive and not counted. Volume discounts apply at 500 and 2,500 students.",
  },
  {
    question: "What compliance standards does Bhapi meet?",
    answer:
      "Bhapi is certified compliant with COPPA 2026, GDPR, FERPA, and LGPD. SOC 2 Type II and ISO 27001 audits are in progress. Full compliance documentation is available on request.",
  },
  {
    question: "Does Bhapi work outside the US?",
    answer:
      "Yes. Bhapi operates in 28 countries with full GDPR support for European families and schools, LGPD support for Brazil, and AU Online Safety compliance for Australia.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "For families we accept all major credit and debit cards via Stripe. Schools can pay by credit card, bank transfer (ACH/SEPA), or purchase order. Enterprise contracts are invoiced quarterly or annually.",
  },
  {
    question: "Can I cancel at any time?",
    answer:
      "Yes. You can cancel your subscription at any time. You'll retain access until the end of your current billing period. We don't pro-rate refunds for partial months, but we'll always work with you if circumstances change.",
  },
];

// --- Components ---

function TierCell({ value }: { value: TierValue }) {
  if (typeof value.value === "boolean") {
    return value.value ? (
      <div className="flex flex-col items-center">
        <Check className="h-5 w-5 text-teal-600" aria-label="Included" />
        {value.note && (
          <span className="mt-1 text-xs text-gray-400">{value.note}</span>
        )}
      </div>
    ) : (
      <X className="h-5 w-5 text-gray-300" aria-label="Not included" />
    );
  }
  if (value.value === null) {
    return <span className="text-sm text-gray-400">—</span>;
  }
  return (
    <div className="flex flex-col items-center">
      <span className="text-sm font-medium text-gray-700">{value.value}</span>
      {value.note && (
        <span className="mt-0.5 text-xs text-gray-400">{value.note}</span>
      )}
    </div>
  );
}

function FaqAccordion({ question, answer }: FaqItem) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-gray-100">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between py-5 text-left"
        aria-expanded={open}
      >
        <span className="text-base font-medium text-gray-900">{question}</span>
        {open ? (
          <ChevronUp className="h-5 w-5 flex-shrink-0 text-gray-400" />
        ) : (
          <ChevronDown className="h-5 w-5 flex-shrink-0 text-gray-400" />
        )}
      </button>
      {open && (
        <p className="pb-5 text-sm leading-relaxed text-gray-600">{answer}</p>
      )}
    </div>
  );
}

// --- Page ---

const TIERS = [
  { key: "free", label: "Free", price: "$0", period: "", cta: "Get Started Free", href: "/register" },
  { key: "family", label: "Family", price: "$9.99", period: "/mo", cta: "Start Free Trial", href: "/register", highlight: true },
  { key: "familyPlus", label: "Family+", price: "$19.99", period: "/mo", cta: "Start Free Trial", href: "/register" },
  { key: "school", label: "School", price: "From $3", period: "/student/mo", cta: "Request Demo", href: "/contact" },
  { key: "enterprise", label: "Enterprise", price: "Custom", period: "", cta: "Contact Sales", href: "/contact" },
] as const;

type TierKey = (typeof TIERS)[number]["key"];

export default function PricingPage() {
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
              href="/register"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-16 text-center">
        <div className="container-narrow mx-auto max-w-2xl">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Simple, transparent pricing
          </h1>
          <p className="mt-4 text-lg text-gray-600">
            Start free. Upgrade when you need more. No hidden fees, ever.
          </p>
        </div>
      </section>

      {/* Plan Header Cards */}
      <section className="pb-8">
        <div className="container-narrow overflow-x-auto">
          <div className="min-w-[900px]">
            <div className="grid grid-cols-6 gap-3">
              {/* Empty label column */}
              <div className="col-span-1" />
              {TIERS.map((tier) => (
                <div
                  key={tier.key}
                  className={`col-span-1 rounded-xl p-5 text-center ${
                    tier.highlight
                      ? "bg-primary-600 text-white shadow-lg ring-2 ring-primary-600"
                      : "bg-white ring-1 ring-gray-200 shadow-sm"
                  }`}
                >
                  {tier.highlight && (
                    <div className="mb-2">
                      <span className="rounded-full bg-white px-3 py-0.5 text-xs font-bold text-primary-700">
                        Most Popular
                      </span>
                    </div>
                  )}
                  <h3
                    className={`text-sm font-bold ${tier.highlight ? "text-white" : "text-gray-900"}`}
                  >
                    {tier.label}
                  </h3>
                  <div className="mt-2 flex items-baseline justify-center gap-0.5">
                    <span
                      className={`text-2xl font-extrabold ${tier.highlight ? "text-white" : "text-gray-900"}`}
                    >
                      {tier.price}
                    </span>
                    {tier.period && (
                      <span
                        className={`text-xs ${tier.highlight ? "text-primary-200" : "text-gray-400"}`}
                      >
                        {tier.period}
                      </span>
                    )}
                  </div>
                  <Link
                    href={tier.href}
                    className={`mt-4 block rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
                      tier.highlight
                        ? "bg-white text-primary-700 hover:bg-primary-50"
                        : "bg-primary-600 text-white hover:bg-primary-700"
                    }`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              ))}
            </div>

            {/* Feature Matrix */}
            <div className="mt-6 rounded-xl ring-1 ring-gray-200 overflow-hidden">
              {FEATURE_ROWS.map((row, i) => (
                <div
                  key={row.label}
                  className={`grid grid-cols-6 gap-3 px-4 py-3 ${
                    i % 2 === 0 ? "bg-white" : "bg-gray-50"
                  }`}
                >
                  <div className="col-span-1 flex items-center text-sm font-medium text-gray-700">
                    {row.label}
                  </div>
                  {(["free", "family", "familyPlus", "school", "enterprise"] as TierKey[]).map(
                    (tierKey) => (
                      <div
                        key={tierKey}
                        className="col-span-1 flex items-center justify-center"
                      >
                        <TierCell value={row[tierKey]} />
                      </div>
                    )
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA row */}
      <section className="py-8">
        <div className="container-narrow overflow-x-auto">
          <div className="min-w-[900px] grid grid-cols-6 gap-3 px-4">
            <div className="col-span-1" />
            {TIERS.map((tier) => (
              <div key={tier.key} className="col-span-1 text-center">
                <Link
                  href={tier.href}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
                >
                  {tier.cta}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-gray-100 bg-gray-50 py-20">
        <div className="container-narrow mx-auto max-w-3xl">
          <h2 className="mb-2 text-3xl font-bold tracking-tight text-gray-900 text-center">
            Frequently asked questions
          </h2>
          <p className="mb-10 text-center text-lg text-gray-600">
            Can&apos;t find the answer you&apos;re looking for?{" "}
            <Link href="/contact" className="text-primary-700 underline hover:text-primary-800">
              Contact us
            </Link>
          </p>
          <div className="rounded-2xl bg-white px-8 shadow-sm ring-1 ring-gray-200">
            {FAQS.map((faq) => (
              <FaqAccordion key={faq.question} {...faq} />
            ))}
          </div>
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
