"use client";

import Link from "next/link";
import {
  Key,
  Webhook,
  Zap,
  Package,
  CheckCircle,
  ArrowRight,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

const FEATURE_CARDS = [
  {
    icon: Key,
    title: "OAuth 2.0",
    description:
      "Secure authorization with PKCE. Issue access tokens scoped to family groups without storing credentials.",
    color: "bg-primary-50 text-primary-600",
  },
  {
    icon: Webhook,
    title: "Webhooks",
    description:
      "Subscribe to real-time events — risk alerts, new members, captured sessions — delivered to your endpoint.",
    color: "bg-teal-50 text-teal-600",
  },
  {
    icon: Zap,
    title: "Rate Limiting",
    description:
      "Transparent rate limits with X-RateLimit headers. Burst-friendly sliding-window algorithm.",
    color: "bg-amber-50 text-amber-600",
  },
  {
    icon: Package,
    title: "SDKs",
    description:
      "Official Python and JavaScript SDKs. Community libraries for Go, Ruby, and more.",
    color: "bg-purple-50 text-purple-600",
  },
];

const TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    calls: "1,000 calls / day",
    highlights: ["Public endpoints", "Community support", "Webhooks (1 endpoint)"],
    cta: "Get Started",
    highlighted: false,
  },
  {
    name: "Starter",
    price: "$49",
    period: "/mo",
    calls: "10,000 calls / day",
    highlights: ["All Free features", "Email support", "Webhooks (10 endpoints)", "OAuth clients (5)"],
    cta: "Start Trial",
    highlighted: false,
  },
  {
    name: "Growth",
    price: "$199",
    period: "/mo",
    calls: "100,000 calls / day",
    highlights: ["All Starter features", "Priority support", "Webhooks (unlimited)", "OAuth clients (25)", "Analytics dashboard"],
    cta: "Start Trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    calls: "Unlimited",
    highlights: ["All Growth features", "SLA guarantee", "Dedicated support", "Custom rate limits", "SSO / SAML"],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export default function DevelopersLandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="mb-16 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-50 px-4 py-1.5 text-sm font-medium text-primary-700">
          <Zap className="h-3.5 w-3.5" />
          Developer Platform — Now in Beta
        </div>
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
          Build on Bhapi
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-600">
          Integrate child safety into your apps. Access real-time risk scores,
          AI usage analytics, and parental controls through a single,
          developer-friendly API.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link href="/developers/dashboard">
            <Button size="lg">
              Apply for Access
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
          <Link href="/developers/docs">
            <Button variant="secondary" size="lg">
              Read the Docs
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mb-16">
        <h2 className="mb-8 text-center text-2xl font-semibold text-gray-900">
          Everything you need to ship safely
        </h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURE_CARDS.map((card) => {
            const Icon = card.icon;
            return (
              <Card key={card.title}>
                <div
                  className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg ${card.color}`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 font-semibold text-gray-900">
                  {card.title}
                </h3>
                <p className="text-sm text-gray-600">{card.description}</p>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Pricing tiers */}
      <section className="mb-16">
        <h2 className="mb-2 text-center text-2xl font-semibold text-gray-900">
          Partnership tiers
        </h2>
        <p className="mb-8 text-center text-sm text-gray-500">
          Start free. Scale as you grow. No surprise fees.
        </p>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-xl border p-6 ${
                tier.highlighted
                  ? "border-primary-300 bg-primary-50 ring-2 ring-primary-300"
                  : "border-gray-200 bg-white"
              }`}
            >
              {tier.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-primary-600 px-3 py-1 text-xs font-semibold text-white">
                    Most Popular
                  </span>
                </div>
              )}
              <p className="mb-1 text-sm font-medium text-gray-500">
                {tier.name}
              </p>
              <p className="mb-1 text-3xl font-bold text-gray-900">
                {tier.price}
                <span className="text-base font-normal text-gray-500">
                  {tier.period}
                </span>
              </p>
              <p className="mb-4 text-xs font-medium text-primary-600">
                {tier.calls}
              </p>
              <ul className="mb-6 space-y-2">
                {tier.highlights.map((h) => (
                  <li key={h} className="flex items-start gap-2 text-sm text-gray-700">
                    <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-teal-500" />
                    {h}
                  </li>
                ))}
              </ul>
              <Link href="/developers/dashboard">
                <Button
                  variant={tier.highlighted ? "primary" : "secondary"}
                  size="sm"
                  className="w-full"
                >
                  {tier.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA banner */}
      <section className="rounded-2xl bg-gray-900 px-8 py-12 text-center text-white">
        <h2 className="mb-3 text-2xl font-semibold">Ready to build?</h2>
        <p className="mb-6 text-gray-400">
          Join developers building safer digital experiences for families and
          schools.
        </p>
        <Link href="/developers/dashboard">
          <Button size="lg" className="bg-primary-500 hover:bg-primary-600 text-white">
            Apply for API Access
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </section>
    </div>
  );
}
