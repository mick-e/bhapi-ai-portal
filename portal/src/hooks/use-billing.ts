"use client";

import { useMutation } from "@tanstack/react-query";
import { billingApi } from "@/lib/api-client";
import type { CheckoutRequest, CheckoutResponse } from "@/types";

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
