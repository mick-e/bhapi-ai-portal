"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface OnboardingStep {
  key: string;
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
}

interface OnboardingProgress {
  user_id: string;
  steps: OnboardingStep[];
  current_step: number;
  total_steps: number;
  completed_count: number;
  is_complete: boolean;
  dismissed: boolean;
}

export function useOnboardingProgress() {
  return useQuery<OnboardingProgress>({
    queryKey: ["onboarding"],
    queryFn: () => api.get<OnboardingProgress>("/api/v1/portal/onboarding"),
    staleTime: 60_000,
  });
}

export function useCompleteOnboardingStep() {
  const queryClient = useQueryClient();
  return useMutation<OnboardingProgress, Error, string>({
    mutationFn: (stepKey) => api.post<OnboardingProgress>("/api/v1/portal/onboarding/complete-step", { step_key: stepKey }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["onboarding"] }),
  });
}

export function useDismissOnboarding() {
  const queryClient = useQueryClient();
  return useMutation<OnboardingProgress, Error, void>({
    mutationFn: () => api.post<OnboardingProgress>("/api/v1/portal/onboarding/dismiss"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["onboarding"] }),
  });
}
