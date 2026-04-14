"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { billingApi } from "@/lib/api-client";
import type {
  CheckoutRequest,
  CheckoutResponse,
  PlansResponse,
  SubscriptionStatus,
  TrialStatus,
} from "@/types";

export function useTrialStatus() {
  return useQuery<TrialStatus>({
    queryKey: ["trial-status"],
    queryFn: () => billingApi.getTrialStatus(),
    staleTime: 60_000,
  });
}

export function useCreateCheckout() {
  return useMutation<CheckoutResponse, Error, CheckoutRequest>({
    mutationFn: (data) => billingApi.createCheckout(data),
    onSuccess: (result) => {
      // Redirect to Stripe Checkout
      window.location.href = result.url;
    },
  });
}

export function useBillingPortal() {
  return useMutation<{ url: string }, Error, void>({
    mutationFn: () => billingApi.getPortalUrl(),
    onSuccess: (result) => {
      window.location.href = result.url;
    },
  });
}

export function useSubscription() {
  return useQuery<SubscriptionStatus>({
    queryKey: ["billing-subscription"],
    queryFn: () => billingApi.getSubscription(),
    staleTime: 60_000,
    retry: false,
  });
}

export function usePlans() {
  return useQuery<PlansResponse>({
    queryKey: ["billing-plans"],
    queryFn: () => billingApi.getPlans(),
    staleTime: 5 * 60_000,
  });
}
