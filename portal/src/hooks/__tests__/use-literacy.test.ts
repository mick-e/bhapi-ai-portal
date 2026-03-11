import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api-client";
import {
  useLiteracyModules,
  useLiteracyQuestions,
  useLiteracyProgress,
  useSubmitAssessment,
  literacyKeys,
  literacyApi,
} from "../use-literacy";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("useLiteracyModules", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches literacy modules", async () => {
    const mockModules = [
      {
        id: "mod1",
        title: "AI Basics",
        description: "Learn the basics",
        category: "fundamentals",
        difficulty_level: "beginner",
        min_age: 8,
        max_age: 12,
        order_index: 1,
        is_active: true,
        question_count: 5,
      },
    ];
    vi.mocked(api.get).mockResolvedValueOnce(mockModules);

    const { result } = renderHook(() => useLiteracyModules(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/literacy/modules")
    );
  });

  it("passes age filter parameters", async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);

    renderHook(() => useLiteracyModules(8, 12), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("min_age=8")
      )
    );
  });

  it("returns error state on failure", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Server error"));

    const { result } = renderHook(() => useLiteracyModules(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useLiteracyQuestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches questions for a module", async () => {
    const mockQuestions = [
      {
        id: "q1",
        module_id: "mod1",
        question_text: "What is AI?",
        question_type: "multiple_choice",
        options: ["A", "B", "C"],
        order_index: 1,
      },
    ];
    vi.mocked(api.get).mockResolvedValueOnce(mockQuestions);

    const { result } = renderHook(() => useLiteracyQuestions("mod1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(api.get).toHaveBeenCalledWith("/api/v1/literacy/modules/mod1/questions");
  });

  it("does not fetch when moduleId is null", () => {
    renderHook(() => useLiteracyQuestions(null), {
      wrapper: createWrapper(),
    });

    expect(api.get).not.toHaveBeenCalled();
  });
});

describe("useLiteracyProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches progress for a member", async () => {
    const mockProgress = {
      member_id: "m1",
      group_id: "g1",
      modules_completed: 2,
      total_score: 80,
      current_level: "intermediate",
    };
    vi.mocked(api.get).mockResolvedValueOnce(mockProgress);

    const { result } = renderHook(() => useLiteracyProgress("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.modules_completed).toBe(2);
    expect(api.get).toHaveBeenCalledWith("/api/v1/literacy/progress/m1");
  });

  it("does not fetch when memberId is null", () => {
    renderHook(() => useLiteracyProgress(null), {
      wrapper: createWrapper(),
    });

    expect(api.get).not.toHaveBeenCalled();
  });
});

describe("useSubmitAssessment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits an assessment", async () => {
    const mockResult = {
      id: "a1",
      group_id: "g1",
      member_id: "m1",
      module_id: "mod1",
      score: 80,
      total_questions: 5,
      correct_count: 4,
      results: [],
      completed_at: "2026-03-11T00:00:00Z",
    };
    vi.mocked(api.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useSubmitAssessment(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      group_id: "g1",
      member_id: "m1",
      module_id: "mod1",
      answers: [{ question_id: "q1", selected_answer: "A" }],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/literacy/assessments",
      expect.objectContaining({ module_id: "mod1" })
    );
  });
});

describe("literacyKeys", () => {
  it("produces correct query keys", () => {
    expect(literacyKeys.all).toEqual(["literacy"]);
    expect(literacyKeys.modules()).toEqual(["literacy", "modules", undefined, undefined]);
    expect(literacyKeys.modules(8, 12)).toEqual(["literacy", "modules", 8, 12]);
    expect(literacyKeys.questions("mod1")).toEqual(["literacy", "questions", "mod1"]);
    expect(literacyKeys.progress("m1")).toEqual(["literacy", "progress", "m1"]);
  });
});
