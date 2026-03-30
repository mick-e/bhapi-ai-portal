"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Shield,
  Users,
  Bell,
  BarChart3,
  ArrowRight,
  Check,
  Monitor,
  BookOpen,
  MapPin,
  Clock,
  GraduationCap,
  Building2,
  Handshake,
  Globe,
  Zap,
} from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";
import { useSocialProof } from "@/hooks/use-social-proof";

type AudienceTab = "families" | "schools" | "partners";

const AUDIENCE_CONTENT: Record<
  AudienceTab,
  {
    headline: string;
    description: string;
    features: { icon: React.ReactNode; title: string; description: string }[];
    cta: { label: string; href: string };
  }
> = {
  families: {
    headline: "Give your family the safest AI experience",
    description:
      "Monitor every AI conversation, set healthy screen time limits, and keep your children safe online — all from one parent dashboard.",
    features: [
      {
        icon: <Shield className="h-5 w-5 text-primary" />,
        title: "AI Usage Monitoring",
        description:
          "See exactly how your children interact with ChatGPT, Gemini, Claude, and 7 other AI platforms in real time.",
      },
      {
        icon: <Users className="h-5 w-5 text-primary" />,
        title: "Safe Social Network",
        description:
          "A moderated social space designed for children under 16, with parent-approved contacts and pre-screened content.",
      },
      {
        icon: <Clock className="h-5 w-5 text-primary" />,
        title: "Screen Time Controls",
        description:
          "Set daily limits, bedtime modes, and app schedules that actually work — enforced at the device level.",
      },
      {
        icon: <MapPin className="h-5 w-5 text-primary" />,
        title: "Location Tracking",
        description:
          "Know where your children are with live location sharing and arrival alerts for places that matter.",
      },
    ],
    cta: { label: "Start Free for Families", href: "/register" },
  },
  schools: {
    headline: "District-wide AI safety, built for educators",
    description:
      "Deploy across your entire district in days. Integrates with Clever and ClassLink. Full COPPA, FERPA, and GDPR compliance included.",
    features: [
      {
        icon: <Monitor className="h-5 w-5 text-accent" />,
        title: "District-wide Deployment",
        description:
          "Roll out to thousands of students in one click using your existing SIS roster and SSO credentials.",
      },
      {
        icon: <BarChart3 className="h-5 w-5 text-accent" />,
        title: "Compliance Dashboard",
        description:
          "COPPA 2026, FERPA, and GDPR compliance reports ready for district administrators and auditors.",
      },
      {
        icon: <GraduationCap className="h-5 w-5 text-accent" />,
        title: "SIS Integration",
        description:
          "Automatic roster sync with Clever and ClassLink — no manual data entry, no CSV uploads.",
      },
      {
        icon: <BookOpen className="h-5 w-5 text-accent" />,
        title: "Bulk Management",
        description:
          "Manage policies, restrictions, and alerts for entire grade levels or individual classrooms.",
      },
    ],
    cta: { label: "Request a School Demo", href: "/contact" },
  },
  partners: {
    headline: "Grow your business with Bhapi",
    description:
      "Join our partner network to offer co-branded AI safety to your customers. Generous revenue share, full deployment support, and a dedicated partner portal.",
    features: [
      {
        icon: <Handshake className="h-5 w-5 text-primary" />,
        title: "Revenue Share",
        description:
          "Earn up to 30% recurring revenue on every customer you refer or co-sell.",
      },
      {
        icon: <Building2 className="h-5 w-5 text-primary" />,
        title: "Co-branded Platform",
        description:
          "White-label the portal with your brand, colours, and domain. Your customers, your relationship.",
      },
      {
        icon: <Zap className="h-5 w-5 text-primary" />,
        title: "Deployment Support",
        description:
          "Dedicated partner success manager, onboarding playbooks, and technical integration support.",
      },
      {
        icon: <Globe className="h-5 w-5 text-primary" />,
        title: "Global Compliance",
        description:
          "Built-in COPPA, GDPR, LGPD, and AU Online Safety compliance — go global without the legal overhead.",
      },
    ],
    cta: { label: "Become a Partner", href: "/contact" },
  },
};

function SocialProofBar() {
  const { data } = useSocialProof();
  const familyCount = data?.familyCount ?? 12000;
  const schoolCount = data?.schoolCount ?? 340;
  const countriesCount = data?.countriesCount ?? 28;

  return (
    <div className="border-y border-gray-100 bg-gray-50 py-6">
      <div className="container-narrow">
        <div className="flex flex-wrap items-center justify-center gap-8 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {familyCount.toLocaleString()}+
            </p>
            <p className="text-sm text-gray-500">Families protected</p>
          </div>
          <div className="hidden h-8 w-px bg-gray-200 sm:block" />
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {schoolCount.toLocaleString()}+
            </p>
            <p className="text-sm text-gray-500">Schools deployed</p>
          </div>
          <div className="hidden h-8 w-px bg-gray-200 sm:block" />
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {countriesCount}
            </p>
            <p className="text-sm text-gray-500">Countries</p>
          </div>
          <div className="hidden h-8 w-px bg-gray-200 sm:block" />
          <div>
            <p className="text-2xl font-bold text-gray-900">COPPA 2026</p>
            <p className="text-sm text-gray-500">Certified compliant</p>
          </div>
        </div>
      </div>
    </div>
  );
}

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
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm text-gray-600">{description}</p>
    </div>
  );
}

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<AudienceTab>("families");
  const content = AUDIENCE_CONTENT[activeTab];

  const tabClass = (tab: AudienceTab) =>
    `px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
      activeTab === tab
        ? "bg-primary-600 text-white shadow-sm"
        : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
    }`;

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100">
        <div className="container-narrow flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <BhapiLogo className="h-8 w-auto" />
          </div>
          <div className="hidden items-center gap-6 sm:flex">
            <Link
              href="/families"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Families
            </Link>
            <Link
              href="/schools"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Schools
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Pricing
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0 z-0"
          aria-hidden="true"
          style={{
            backgroundImage: "url('/hero-bg.svg')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
            opacity: 0.35,
          }}
        />
        <div className="container-narrow relative z-10 py-20 sm:py-28">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-4 py-1.5">
              <Shield className="h-4 w-4 text-primary-600" />
              <span className="text-sm font-medium text-primary-700">
                COPPA 2026 Certified
              </span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Safe AI.{" "}
              <span className="text-primary">Safe Social.</span>{" "}
              <span className="text-accent">One Platform.</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Monitor your child&apos;s AI interactions and social activity in
              one place. Real-time alerts, screen time controls, and a safe
              social network built for children under 16.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Start Free
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            {/* App Store Badges — hidden until mobile apps are published */}
          </div>
        </div>
      </section>

      {/* Social Proof Bar */}
      <SocialProofBar />

      {/* Audience Tabs */}
      <section className="py-20">
        <div className="container-narrow">
          {/* Tab Switcher */}
          <div className="mx-auto mb-12 flex max-w-sm items-center justify-center rounded-xl bg-gray-100 p-1.5 gap-1">
            <button
              onClick={() => setActiveTab("families")}
              className={tabClass("families")}
              aria-selected={activeTab === "families"}
              role="tab"
            >
              Families
            </button>
            <button
              onClick={() => setActiveTab("schools")}
              className={tabClass("schools")}
              aria-selected={activeTab === "schools"}
              role="tab"
            >
              Schools
            </button>
            <button
              onClick={() => setActiveTab("partners")}
              className={tabClass("partners")}
              aria-selected={activeTab === "partners"}
              role="tab"
            >
              Partners
            </button>
          </div>

          {/* Tab Content */}
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              {content.headline}
            </h2>
            <p className="mt-4 text-lg text-gray-600">{content.description}</p>
          </div>
          <div className="mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {content.features.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>
          <div className="mt-10 text-center">
            <Link
              href={content.cta.href}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
            >
              {content.cta.label}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Compliance Strip */}
      <section className="border-y border-gray-100 bg-gray-50 py-10">
        <div className="container-narrow">
          <p className="mb-6 text-center text-sm font-medium uppercase tracking-widest text-gray-400">
            Trusted Compliance
          </p>
          <div className="flex flex-wrap items-center justify-center gap-6">
            {["COPPA 2026", "GDPR", "FERPA", "LGPD", "AU Online Safety"].map(
              (badge) => (
                <span
                  key={badge}
                  className="rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm font-semibold text-gray-700 shadow-sm"
                >
                  {badge}
                </span>
              )
            )}
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20">
        <div className="container-narrow">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Simple, transparent pricing
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Start free. Upgrade when you&apos;re ready. No hidden fees.
            </p>
          </div>
          <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
            <PricingCard
              name="Free"
              price="$0"
              period="/mo"
              description="For families getting started"
              features={["1 child profile", "Basic AI monitoring", "Email alerts"]}
              cta={{ label: "Get Started Free", href: "/register" }}
            />
            <PricingCard
              name="Family"
              price="$9.99"
              period="/mo"
              description="For growing families"
              features={[
                "Up to 3 children",
                "Full AI monitoring",
                "Safe social network",
                "Screen time controls",
              ]}
              highlighted
              cta={{ label: "Start Free Trial", href: "/register" }}
            />
            <PricingCard
              name="School"
              price="Custom"
              period=""
              description="Per-seat pricing for districts"
              features={[
                "Unlimited students",
                "SIS integration",
                "Compliance dashboard",
                "Priority support",
              ]}
              cta={{ label: "Contact Sales", href: "/contact" }}
            />
          </div>
          <div className="mt-8 text-center">
            <Link
              href="/pricing"
              className="text-sm font-medium text-primary-700 hover:text-primary-800 underline underline-offset-2"
            >
              View full pricing comparison
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="container-narrow py-12">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex items-center gap-2">
              <BhapiLogo className="h-5 w-auto" />
            </div>
            <nav className="flex flex-wrap items-center gap-6 text-sm text-gray-500">
              <Link href="/families" className="hover:text-gray-900">
                Families
              </Link>
              <Link href="/schools" className="hover:text-gray-900">
                Schools
              </Link>
              <Link href="/pricing" className="hover:text-gray-900">
                Pricing
              </Link>
              <Link href="/legal/privacy" className="hover:text-gray-900">
                Privacy
              </Link>
              <Link href="/legal/terms" className="hover:text-gray-900">
                Terms
              </Link>
            </nav>
            <p className="text-sm text-gray-500">
              &copy; {new Date().getFullYear()} Bhapi. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function PricingCard({
  name,
  price,
  period,
  description,
  features,
  highlighted = false,
  cta,
}: {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  cta: { label: string; href: string };
}) {
  return (
    <div
      className={`rounded-xl p-8 flex flex-col ${
        highlighted
          ? "bg-primary-600 text-white ring-2 ring-primary-600 shadow-lg"
          : "bg-white ring-1 ring-gray-200 shadow-sm"
      }`}
    >
      <h3
        className={`text-lg font-bold ${highlighted ? "text-white" : "text-gray-900"}`}
      >
        {name}
      </h3>
      <div className="mt-2 flex items-baseline gap-1">
        <span
          className={`text-3xl font-bold ${highlighted ? "text-white" : "text-gray-900"}`}
        >
          {price}
        </span>
        {period && (
          <span
            className={`text-sm ${highlighted ? "text-primary-200" : "text-gray-500"}`}
          >
            {period}
          </span>
        )}
      </div>
      <p
        className={`mt-1 text-sm ${highlighted ? "text-primary-100" : "text-gray-600"}`}
      >
        {description}
      </p>
      <ul className="mt-6 space-y-2.5 flex-1">
        {features.map((feature) => (
          <li key={feature} className="flex items-center gap-2 text-sm">
            <Check
              className={`h-4 w-4 flex-shrink-0 ${highlighted ? "text-primary-200" : "text-primary"}`}
            />
            <span className={highlighted ? "text-primary-50" : "text-gray-700"}>
              {feature}
            </span>
          </li>
        ))}
      </ul>
      <Link
        href={cta.href}
        className={`mt-6 block rounded-lg px-4 py-2.5 text-center text-sm font-semibold transition-colors ${
          highlighted
            ? "bg-white text-primary-700 hover:bg-primary-50"
            : "bg-primary-600 text-white hover:bg-primary-700"
        }`}
      >
        {cta.label}
      </Link>
    </div>
  );
}
