import Link from "next/link";
import { Users, Bell, BarChart3, ArrowRight, Check } from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100">
        <div className="container-narrow flex h-16 items-center justify-between">
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
              href="/register"
              className="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Bhapi yellow pattern background */}
        <div
          className="absolute inset-0 z-0"
          aria-hidden="true"
          style={{
            backgroundImage: "url('/hero-bg.svg')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
          }}
        />
        <div className="container-narrow relative z-10 py-24 sm:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              AI Safety for{" "}
              <span className="text-primary">Families</span>,{" "}
              <span className="text-accent">Schools</span> &{" "}
              <span className="text-primary-700">Clubs</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 font-bold">
              Monitor, manage, and protect how your group uses AI. Get real-time
              alerts for risky content, track spending, and ensure safe AI
              interactions for everyone you care about.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Create Free Account
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
              >
                Log In
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50 py-24">
        <div className="container-narrow">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Everything you need to keep AI safe
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              A single portal for families, schools, and clubs to oversee AI
              usage with confidence.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <FeatureCard
              icon={<Users className="h-6 w-6 text-primary" />}
              title="Member Management"
              description="Add and manage family members, students, or club members with individual safety profiles."
            />
            <FeatureCard
              icon={<Bell className="h-6 w-6 text-primary" />}
              title="Real-time Alerts"
              description="Get instant notifications when AI interactions trigger safety concerns."
            />
            <FeatureCard
              icon={<BarChart3 className="h-6 w-6 text-primary" />}
              title="Spend Tracking"
              description="Monitor AI API costs and set budgets per member or for the entire group."
            />
            <FeatureCard
              icon={<BarChart3 className="h-6 w-6 text-primary" />}
              title="Safety Reports"
              description="Comprehensive reports on AI usage patterns, risks, and compliance."
            />
          </div>
        </div>
      </section>

      {/* Account Types Section */}
      <section className="py-24">
        <div className="container-narrow">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Built for your group
            </h2>
          </div>
          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-3">
            <AccountTypeCard
              title="Families"
              price="$9.99/mo"
              description="Protect your children and manage AI usage across the household."
              features={[
                "Per-child safety profiles",
                "Age-appropriate content filtering",
                "Shared family spend limits",
              ]}
              cta={{ label: "Get Started", href: "/register" }}
            />
            <AccountTypeCard
              title="Schools"
              price="Custom pricing"
              description="Safeguard students and empower teachers with AI oversight tools."
              features={[
                "Classroom-level controls",
                "Teacher and student roles",
                "Compliance reporting",
              ]}
              highlighted
              cta={{ label: "Contact Sales", href: "mailto:sales@bhapi.ai" }}
            />
            <AccountTypeCard
              title="Clubs"
              price="Custom pricing"
              description="Keep your organisation safe with group-wide AI governance."
              features={[
                "Custom member roles",
                "Activity monitoring",
                "Budget management",
              ]}
              cta={{ label: "Contact Sales", href: "mailto:sales@bhapi.ai" }}
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="container-narrow py-12">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-2">
              <BhapiLogo className="h-5 w-auto" />
            </div>
            <p className="text-sm text-gray-500">
              &copy; {new Date().getFullYear()} Bhapi. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
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

function AccountTypeCard({
  title,
  price,
  description,
  features,
  highlighted = false,
  cta,
}: {
  title: string;
  price: string;
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
        className={`text-xl font-bold ${
          highlighted ? "text-white" : "text-gray-900"
        }`}
      >
        {title}
      </h3>
      <p
        className={`mt-1 text-2xl font-bold ${
          highlighted ? "text-white" : "text-gray-900"
        }`}
      >
        {price}
      </p>
      <p
        className={`mt-2 text-sm ${
          highlighted ? "text-primary-100" : "text-gray-600"
        }`}
      >
        {description}
      </p>
      <ul className="mt-6 space-y-3 flex-1">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm">
            <Check
              className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                highlighted ? "text-primary-200" : "text-primary"
              }`}
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
