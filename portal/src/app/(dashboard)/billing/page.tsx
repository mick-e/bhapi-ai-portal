"use client";

import {
  Loader2,
  AlertTriangle,
  CreditCard,
  ExternalLink,
  Check,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import {
  useBillingPortal,
  useCreateCheckout,
  usePlans,
  useSubscription,
} from "@/hooks/use-billing";
import { useTranslations } from "@/contexts/LocaleContext";
import type { BillingPlan } from "@/types";

export default function BillingPage() {
  const t = useTranslations("billing");

  const {
    data: subscription,
    isLoading: subLoading,
    isError: subError,
    error: subErr,
    refetch: refetchSub,
  } = useSubscription();

  const {
    data: plansData,
    isLoading: plansLoading,
    isError: plansError,
  } = usePlans();

  const openPortal = useBillingPortal();
  const createCheckout = useCreateCheckout();

  if (subLoading || plansLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">{t("loading")}</span>
      </div>
    );
  }

  // Subscription 404 is expected for free-plan / no-subscription users.
  // Only treat plans error as a hard failure.
  if (plansError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">{t("error")}</p>
        <p className="mt-1 text-sm text-gray-500">
          {(subErr as Error)?.message || ""}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetchSub()}
        >
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  const plans = plansData?.plans ?? {};
  const planKeys = Object.keys(plans);

  const currentPlanKey = subscription?.plan_type ?? "free";
  const currentPlan = plans[currentPlanKey];
  const hasPaidSubscription =
    !!subscription &&
    subscription.plan_type !== "free" &&
    ["active", "trialing", "past_due"].includes(subscription.status);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("description")}</p>
      </div>

      {subError && !hasPaidSubscription && (
        <div className="mb-6 flex items-start gap-3 rounded-lg bg-amber-50 p-4 ring-1 ring-amber-200">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-500" />
          <p className="text-sm text-amber-900">
            {(subErr as Error)?.message || t("error")}
          </p>
        </div>
      )}

      {/* Current plan */}
      <Card title={t("currentPlan")}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-gray-400" />
              <span className="text-lg font-semibold text-gray-900">
                {currentPlan?.name ?? t("freePlan")}
              </span>
              <Badge variant={statusVariant(subscription?.status)}>
                {formatStatus(subscription?.status)}
              </Badge>
            </div>
            {currentPlan?.description && (
              <p className="mt-2 text-sm text-gray-500">
                {currentPlan.description}
              </p>
            )}
            {subscription?.current_period_end && (
              <p className="mt-2 text-xs text-gray-400">
                {t("renewsOn")}{" "}
                {new Date(
                  subscription.current_period_end
                ).toLocaleDateString()}
              </p>
            )}
            {subscription?.trial_end && subscription.status === "trialing" && (
              <p className="mt-2 text-xs text-gray-400">
                {t("trialEnds")}{" "}
                {new Date(subscription.trial_end).toLocaleDateString()}
              </p>
            )}
          </div>
          {hasPaidSubscription && (
            <Button
              variant="secondary"
              onClick={() => openPortal.mutate()}
              isLoading={openPortal.isPending}
            >
              <ExternalLink className="h-4 w-4" />
              {t("manageBilling")}
            </Button>
          )}
        </div>
      </Card>

      {/* Available plans */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          {t("availablePlans")}
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {planKeys.map((key) => (
            <PlanCard
              key={key}
              planKey={key}
              plan={plans[key]}
              isCurrent={key === currentPlanKey}
              onSelect={() =>
                createCheckout.mutate({
                  plan_type: key,
                  billing_cycle: "monthly",
                })
              }
              selecting={
                createCheckout.isPending &&
                createCheckout.variables?.plan_type === key
              }
              t={t}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function PlanCard({
  planKey,
  plan,
  isCurrent,
  onSelect,
  selecting,
  t,
}: {
  planKey: string;
  plan: BillingPlan;
  isCurrent: boolean;
  onSelect: () => void;
  selecting: boolean;
  t: (key: string) => string;
}) {
  const priceLabel = formatPrice(plan);
  const isFree = planKey === "free";
  const isContactSales = plan.price_monthly === null && !isFree;

  return (
    <div
      className={`flex flex-col rounded-xl bg-white p-6 shadow-sm ring-1 ${
        isCurrent ? "ring-2 ring-primary-600" : "ring-gray-200"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{plan.name}</h3>
          <p className="mt-1 text-xs text-gray-500">{plan.description}</p>
        </div>
        {isCurrent && <Badge variant="success">{t("yourPlan")}</Badge>}
      </div>

      <div className="mt-4">
        <p className="text-2xl font-bold text-gray-900">{priceLabel}</p>
        {plan.price_unit && (
          <p className="mt-0.5 text-xs text-gray-400">{plan.price_unit}</p>
        )}
      </div>

      <ul className="mt-4 flex-1 space-y-2">
        {plan.features.slice(0, 6).map((feature, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
            <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary-600" />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <div className="mt-6">
        {isCurrent ? (
          <Button variant="secondary" className="w-full" disabled>
            {t("currentlyActive")}
          </Button>
        ) : isFree ? (
          <Button variant="ghost" className="w-full" disabled>
            {t("freePlan")}
          </Button>
        ) : isContactSales ? (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              window.location.href = "mailto:sales@bhapi.ai";
            }}
          >
            {t("contactSales")}
          </Button>
        ) : (
          <Button
            variant="primary"
            className="w-full"
            onClick={onSelect}
            isLoading={selecting}
          >
            {t("selectPlan")}
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatPrice(plan: BillingPlan): string {
  if (plan.price_monthly === 0) return "$0";
  if (plan.price_monthly === null || plan.price_monthly === undefined)
    return "Custom";
  return `$${plan.price_monthly.toFixed(2)}/mo`;
}

function statusVariant(status: string | undefined): BadgeVariant {
  switch (status) {
    case "active":
      return "success";
    case "trialing":
      return "info";
    case "past_due":
      return "warning";
    case "canceled":
    case "cancelled":
    case "unpaid":
      return "error";
    default:
      return "neutral";
  }
}

function formatStatus(status: string | undefined): string {
  if (!status) return "Free";
  return status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, " ");
}
