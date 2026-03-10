"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LiteracyModule {
  id: string;
  title: string;
  description: string;
  category: string;
  difficulty_level: string;
  min_age: number;
  max_age: number;
  order_index: number;
  is_active: boolean;
  question_count: number;
}

export interface LiteracyQuestion {
  id: string;
  module_id: string;
  question_text: string;
  question_type: "multiple_choice" | "true_false";
  options: string[];
  order_index: number;
}

export interface QuestionResult {
  question_id: string;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
}

export interface AssessmentResponse {
  id: string;
  group_id: string;
  member_id: string;
  module_id: string;
  score: number;
  total_questions: number;
  correct_count: number;
  results: QuestionResult[];
  completed_at: string;
}

export interface AssessmentSubmit {
  group_id: string;
  member_id: string;
  module_id: string;
  answers: { question_id: string; selected_answer: string }[];
}

export interface LiteracyProgress {
  member_id: string;
  group_id: string;
  modules_completed: number;
  total_score: number;
  current_level: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const literacyKeys = {
  all: ["literacy"] as const,
  modules: (minAge?: number, maxAge?: number) =>
    [...literacyKeys.all, "modules", minAge, maxAge] as const,
  questions: (moduleId: string) =>
    [...literacyKeys.all, "questions", moduleId] as const,
  progress: (memberId: string) =>
    [...literacyKeys.all, "progress", memberId] as const,
};

// ─── API Client ──────────────────────────────────────────────────────────────

function qs(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ""
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const literacyApi = {
  listModules(minAge?: number, maxAge?: number): Promise<LiteracyModule[]> {
    return api.get<LiteracyModule[]>(
      `/api/v1/literacy/modules${qs({ min_age: minAge, max_age: maxAge })}`
    );
  },

  getQuestions(moduleId: string): Promise<LiteracyQuestion[]> {
    return api.get<LiteracyQuestion[]>(
      `/api/v1/literacy/modules/${moduleId}/questions`
    );
  },

  submitAssessment(data: AssessmentSubmit): Promise<AssessmentResponse> {
    return api.post<AssessmentResponse>("/api/v1/literacy/assessments", data);
  },

  getProgress(memberId: string): Promise<LiteracyProgress> {
    return api.get<LiteracyProgress>(
      `/api/v1/literacy/progress/${memberId}`
    );
  },

  seed(): Promise<{ modules_created: number }> {
    return api.post<{ modules_created: number }>("/api/v1/literacy/seed");
  },
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useLiteracyModules(minAge?: number, maxAge?: number) {
  return useQuery<LiteracyModule[]>({
    queryKey: literacyKeys.modules(minAge, maxAge),
    queryFn: () => literacyApi.listModules(minAge, maxAge),
  });
}

export function useLiteracyQuestions(moduleId: string | null) {
  return useQuery<LiteracyQuestion[]>({
    queryKey: literacyKeys.questions(moduleId || ""),
    queryFn: () => literacyApi.getQuestions(moduleId!),
    enabled: !!moduleId,
  });
}

export function useLiteracyProgress(memberId: string | null) {
  return useQuery<LiteracyProgress>({
    queryKey: literacyKeys.progress(memberId || ""),
    queryFn: () => literacyApi.getProgress(memberId!),
    enabled: !!memberId,
  });
}

export function useSubmitAssessment() {
  const queryClient = useQueryClient();

  return useMutation<AssessmentResponse, Error, AssessmentSubmit>({
    mutationFn: (data) => literacyApi.submitAssessment(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: literacyKeys.progress(variables.member_id),
      });
      queryClient.invalidateQueries({
        queryKey: literacyKeys.modules(),
      });
    },
  });
}
