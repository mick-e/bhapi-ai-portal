"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Shield,
  Users,
  Clock,
  MapPin,
  Palette,
  Bell,
  Check,
  Star,
  ArrowRight,
} from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-50">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-gray-600">{description}</p>
    </div>
  );
}

interface PlanCardProps {
  name: string;
  price: string;
  period: string;
  description: string;
  children: string;
  features: string[];
  highlighted?: boolean;
  badge?: string;
  cta: string;
}

function PlanCard({
  name,
  price,
  period,
  description,
  children,
  features,
  highlighted = false,
  badge,
  cta,
}: PlanCardProps) {
  return (
    <div
      className={`relative flex flex-col rounded-2xl p-8 ${
        highlighted
          ? "bg-primary-600 text-white shadow-xl ring-2 ring-primary-600"
          : "bg-white shadow-sm ring-1 ring-gray-200"
      }`}
    >
      {badge && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="rounded-full bg-accent px-4 py-1 text-xs font-bold uppercase tracking-wide text-white shadow">
            {badge}
          </span>
        </div>
      )}
      <div>
        <h3
          className={`text-lg font-bold ${highlighted ? "text-white" : "text-gray-900"}`}
        >
          {name}
        </h3>
        <div className="mt-3 flex items-baseline gap-1">
          <span
            className={`text-4xl font-extrabold ${highlighted ? "text-white" : "text-gray-900"}`}
          >
            {price}
          </span>
          {period && (
            <span
              className={`text-sm font-medium ${highlighted ? "text-primary-200" : "text-gray-500"}`}
            >
              {period}
            </span>
          )}
        </div>
        <p
          className={`mt-1 text-sm ${highlighted ? "text-primary-100" : "text-gray-500"}`}
        >
          {description}
        </p>
        <p
          className={`mt-1 text-xs font-medium ${highlighted ? "text-primary-200" : "text-gray-400"}`}
        >
          {children}
        </p>
      </div>
      <ul className="mt-8 flex-1 space-y-3">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-3 text-sm">
            <Check
              className={`mt-0.5 h-4 w-4 flex-shrink-0 ${highlighted ? "text-primary-200" : "text-primary-600"}`}
            />
            <span className={highlighted ? "text-primary-50" : "text-gray-700"}>
              {f}
            </span>
          </li>
        ))}
      </ul>
      <Link
        href="/register"
        className={`mt-8 block rounded-xl px-5 py-3 text-center text-sm font-bold transition-colors ${
          highlighted
            ? "bg-white text-primary-700 hover:bg-primary-50"
            : "bg-primary-600 text-white hover:bg-primary-700"
        }`}
      >
        {cta}
      </Link>
    </div>
  );
}

interface TestimonialProps {
  quote: string;
  name: string;
  role: string;
  rating: number;
}

function Testimonial({ quote, name, role, rating }: TestimonialProps) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="mb-3 flex gap-1">
        {Array.from({ length: rating }).map((_, i) => (
          <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
        ))}
      </div>
      <p className="text-sm leading-relaxed text-gray-700 italic">
        &ldquo;{quote}&rdquo;
      </p>
      <div className="mt-4">
        <p className="text-sm font-semibold text-gray-900">{name}</p>
        <p className="text-xs text-gray-500">{role}</p>
      </div>
    </div>
  );
}

const FEATURES = [
  {
    icon: <Shield className="h-6 w-6 text-primary-600" />,
    title: "AI Monitoring",
    description:
      "See every conversation your children have with ChatGPT, Gemini, Claude, and 7 more AI platforms. Get instant alerts for anything concerning.",
  },
  {
    icon: <Users className="h-6 w-6 text-primary-600" />,
    title: "Safe Social Network",
    description:
      "A moderated social space built for under-16s. Parent-approved contacts, pre-screened posts, and no ads. Social fun without the risks.",
  },
  {
    icon: <Clock className="h-6 w-6 text-primary-600" />,
    title: "Screen Time Controls",
    description:
      "Set daily limits, homework hours, and bedtime modes. Device-level enforcement means the rules actually stick.",
  },
  {
    icon: <MapPin className="h-6 w-6 text-primary-600" />,
    title: "Location Tracking",
    description:
      "Live location sharing and arrival alerts for home, school, and trusted places — with privacy controls children can understand.",
  },
  {
    icon: <Palette className="h-6 w-6 text-primary-600" />,
    title: "Creative Tools",
    description:
      "Age-appropriate AI creative tools for art, stories, and learning — all supervised and safe. Available on Family+ plan.",
  },
  {
    icon: <Bell className="h-6 w-6 text-primary-600" />,
    title: "Real-time Alerts",
    description:
      "Instant push notifications when Bhapi detects risk — from concerning AI content to location anomalies. You'll always know first.",
  },
];

const PLANS: PlanCardProps[] = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    description: "Get started at no cost",
    children: "1 child",
    features: [
      "1 child profile",
      "Basic AI monitoring (3 platforms)",
      "Email alerts",
      "7-day activity history",
    ],
    cta: "Get Started Free",
  },
  {
    name: "Family",
    price: "$9.99",
    period: "/mo",
    description: "Everything a family needs",
    children: "Up to 3 children",
    features: [
      "Up to 3 child profiles",
      "Full AI monitoring (10 platforms)",
      "Safe social network",
      "Screen time controls",
      "Location tracking",
      "Push + SMS alerts",
      "90-day activity history",
      "Weekly family digest",
    ],
    highlighted: true,
    badge: "Most Popular",
    cta: "Start 14-Day Free Trial",
  },
  {
    name: "Family+",
    price: "$19.99",
    period: "/mo",
    description: "For larger families",
    children: "Up to 5 children",
    features: [
      "Up to 5 child profiles",
      "Everything in Family",
      "Creative AI tools",
      "Sibling privacy controls",
      "Priority support",
      "Unlimited activity history",
      "Custom alert rules",
    ],
    cta: "Start 14-Day Free Trial",
  },
];

const TESTIMONIALS: TestimonialProps[] = [
  {
    quote:
      "I can finally feel relaxed when my daughter uses AI for homework. Bhapi shows me exactly what she's asking and flags anything I should know about.",
    name: "Sarah M.",
    role: "Parent of a 12-year-old",
    rating: 5,
  },
  {
    quote:
      "The safe social network is a game-changer. My son has a place to connect with friends without me worrying about who he's talking to or what he's seeing.",
    name: "James T.",
    role: "Parent of a 10-year-old",
    rating: 5,
  },
  {
    quote:
      "Screen time was a constant battle. With Bhapi the limits are automatic — my kids know the rules and there's no arguing about it.",
    name: "Priya K.",
    role: "Parent of 3 children",
    rating: 5,
  },
];

export default function FamiliesPage() {
  const [billingCycle] = useState<"monthly">("monthly");

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
      <section className="bg-gradient-to-b from-primary-50 to-white py-20">
        <div className="container-narrow mx-auto max-w-3xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-100 px-4 py-1.5">
            <Shield className="h-4 w-4 text-primary-600" />
            <span className="text-sm font-semibold text-primary-700">
              Trusted by 12,000+ families
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            The safest way for your family to use AI
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-600">
            Monitor AI interactions, manage screen time, and keep your children
            safe on social — all from one parent dashboard. Start free, no credit
            card required.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700"
            >
              Start Your Free Trial
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Book a Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="container-narrow">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Everything your family needs — in one place
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Purpose-built for families. Not repurposed enterprise software.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <FeatureCard key={f.title} {...f} />
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-gray-50 py-20">
        <div className="container-narrow">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Simple family pricing
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Start free. Upgrade when you need more. Cancel any time.
            </p>
          </div>
          <div
            className="mx-auto grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-3"
            aria-label={`${billingCycle} pricing`}
          >
            {PLANS.map((plan) => (
              <PlanCard key={plan.name} {...plan} />
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-gray-500">
            All paid plans include a 14-day free trial. No credit card required
            to start.
          </p>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20">
        <div className="container-narrow">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Loved by families worldwide
            </h2>
          </div>
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <Testimonial key={t.name} {...t} />
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-primary-600 py-16">
        <div className="container-narrow text-center">
          <h2 className="text-3xl font-bold text-white">
            Ready to protect your family?
          </h2>
          <p className="mt-4 text-lg text-primary-100">
            Join 12,000+ families who trust Bhapi. Start free today.
          </p>
          <Link
            href="/register"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3 text-base font-bold text-primary-700 shadow-sm hover:bg-primary-50 transition-colors"
          >
            Start Your Free Trial
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
