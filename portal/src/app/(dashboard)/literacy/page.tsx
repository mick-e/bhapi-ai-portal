"use client";

import { useState, Suspense } from "react";
import {
  BookOpen,
  Loader2,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  Trophy,
  Star,
  GraduationCap,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import {
  useLiteracyModules,
  useLiteracyQuestions,
  useLiteracyProgress,
  useSubmitAssessment,
} from "@/hooks/use-literacy";
import type {
  LiteracyModule,
  LiteracyQuestion,
  AssessmentResponse,
} from "@/hooks/use-literacy";

// ─── Difficulty Badge ────────────────────────────────────────────────────────

function DifficultyBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    beginner: "bg-green-100 text-green-700",
    intermediate: "bg-amber-100 text-amber-700",
    advanced: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colors[level] || "bg-gray-100 text-gray-700"}`}
    >
      {level}
    </span>
  );
}

// ─── Level Icon ──────────────────────────────────────────────────────────────

function LevelIcon({ level }: { level: string }) {
  if (level === "advanced") return <Trophy className="h-5 w-5 text-amber-500" />;
  if (level === "intermediate") return <Star className="h-5 w-5 text-primary-500" />;
  return <GraduationCap className="h-5 w-5 text-green-500" />;
}

// ─── Progress Card ───────────────────────────────────────────────────────────

function ProgressCard({ memberId }: { memberId: string }) {
  const { data: progress, isLoading } = useLiteracyProgress(memberId);

  if (isLoading) return null;
  if (!progress) return null;

  return (
    <Card className="mb-6">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-50">
          <LevelIcon level={progress.current_level} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">Your Progress</h3>
            <DifficultyBadge level={progress.current_level} />
          </div>
          <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
            <span>{progress.modules_completed} modules completed</span>
            <span>Average score: {progress.total_score.toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Module Card ─────────────────────────────────────────────────────────────

function ModuleCard({
  module,
  onStart,
}: {
  module: LiteracyModule;
  onStart: (id: string) => void;
}) {
  const categoryLabels: Record<string, string> = {
    fundamentals: "Fundamentals",
    safety: "Safety",
    privacy: "Privacy",
    critical_thinking: "Critical Thinking",
    misinformation: "Misinformation",
    ethics: "Ethics",
  };

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">{module.title}</h3>
            <DifficultyBadge level={module.difficulty_level} />
          </div>
          <p className="mt-1 text-sm text-gray-500">{module.description}</p>
          <div className="mt-3 flex items-center gap-3 text-xs text-gray-400">
            <span>{categoryLabels[module.category] || module.category}</span>
            <span>Ages {module.min_age}-{module.max_age}</span>
            <span>{module.question_count} questions</span>
          </div>
        </div>
      </div>
      <div className="mt-4">
        <Button size="sm" onClick={() => onStart(module.id)}>
          <BookOpen className="h-4 w-4" />
          Start Quiz
        </Button>
      </div>
    </Card>
  );
}

// ─── Quiz Interface ──────────────────────────────────────────────────────────

function QuizView({
  module,
  questions,
  groupId,
  memberId,
  onBack,
}: {
  module: LiteracyModule;
  questions: LiteracyQuestion[];
  groupId: string;
  memberId: string;
  onBack: () => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AssessmentResponse | null>(null);
  const submitMutation = useSubmitAssessment();

  const currentQuestion = questions[currentIndex];
  const totalQuestions = questions.length;
  const isLastQuestion = currentIndex === totalQuestions - 1;
  const allAnswered = Object.keys(answers).length === totalQuestions;

  function handleSelect(answer: string) {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: answer }));
  }

  function handleNext() {
    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  }

  function handlePrev() {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  }

  async function handleSubmit() {
    const answerList = Object.entries(answers).map(([question_id, selected_answer]) => ({
      question_id,
      selected_answer,
    }));

    const res = await submitMutation.mutateAsync({
      group_id: groupId,
      member_id: memberId,
      module_id: module.id,
      answers: answerList,
    });

    setResult(res);
  }

  // ─── Results View ────────────────────────────────────────────────

  if (result) {
    return (
      <div>
        <Button variant="ghost" size="sm" onClick={onBack} className="mb-4">
          <ArrowLeft className="h-4 w-4" />
          Back to Modules
        </Button>

        <Card className="mb-6">
          <div className="text-center py-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary-50 mb-4">
              <Trophy className="h-8 w-8 text-primary-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">Quiz Complete!</h2>
            <p className="mt-1 text-sm text-gray-500">{module.title}</p>
            <p className="mt-4 text-3xl font-bold text-primary-600">
              {result.score.toFixed(0)}%
            </p>
            <p className="mt-1 text-sm text-gray-500">
              {result.correct_count} of {result.total_questions} correct
            </p>
          </div>
        </Card>

        <div className="space-y-4">
          {result.results.map((r, idx) => {
            const question = questions.find((q) => q.id === r.question_id);
            return (
              <Card key={r.question_id}>
                <div className="flex items-start gap-3">
                  {r.is_correct ? (
                    <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
                  ) : (
                    <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {idx + 1}. {question?.question_text}
                    </p>
                    <p className="mt-1 text-sm text-gray-600">
                      Your answer: <span className={r.is_correct ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                        {r.selected_answer}
                      </span>
                    </p>
                    {!r.is_correct && (
                      <p className="mt-0.5 text-sm text-gray-600">
                        Correct answer: <span className="text-green-600 font-medium">{r.correct_answer}</span>
                      </p>
                    )}
                    <p className="mt-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
                      {r.explanation}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    );
  }

  // ─── Question View ───────────────────────────────────────────────

  return (
    <div>
      <Button variant="ghost" size="sm" onClick={onBack} className="mb-4">
        <ArrowLeft className="h-4 w-4" />
        Back to Modules
      </Button>

      <Card>
        <div className="mb-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">{module.title}</h2>
            <span className="text-sm text-gray-500">
              Question {currentIndex + 1} of {totalQuestions}
            </span>
          </div>
          <div className="mt-2 h-2 w-full rounded-full bg-gray-100">
            <div
              className="h-2 rounded-full bg-primary-500 transition-all"
              style={{
                width: `${((currentIndex + 1) / totalQuestions) * 100}%`,
              }}
            />
          </div>
        </div>

        <p className="mb-6 text-base font-medium text-gray-900">
          {currentQuestion.question_text}
        </p>

        <div className="space-y-3">
          {currentQuestion.options.map((option) => {
            const isSelected = answers[currentQuestion.id] === option;
            return (
              <button
                key={option}
                type="button"
                onClick={() => handleSelect(option)}
                className={`w-full rounded-lg border-2 px-4 py-3 text-left text-sm font-medium transition-colors ${
                  isSelected
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <Button
            variant="secondary"
            size="sm"
            onClick={handlePrev}
            disabled={currentIndex === 0}
          >
            Previous
          </Button>

          <div className="flex gap-2">
            {isLastQuestion && allAnswered ? (
              <Button
                size="sm"
                onClick={handleSubmit}
                isLoading={submitMutation.isPending}
              >
                Submit Quiz
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleNext}
                disabled={!answers[currentQuestion.id] || isLastQuestion}
              >
                Next
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

// ─── Main Page Content ───────────────────────────────────────────────────────

function LiteracyPageContent() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [ageFilter, setAgeFilter] = useState<number | undefined>(undefined);

  const {
    data: modules,
    isLoading: modulesLoading,
    isError: modulesError,
    error: modulesErr,
    refetch: refetchModules,
  } = useLiteracyModules(ageFilter, ageFilter);

  const {
    data: questions,
    isLoading: questionsLoading,
  } = useLiteracyQuestions(selectedModuleId);

  const selectedModule = modules?.find((m) => m.id === selectedModuleId) || null;

  if (modulesLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading modules...</span>
      </div>
    );
  }

  if (modulesError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load literacy modules
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(modulesErr as Error)?.message || "Something went wrong"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetchModules()}
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  // Quiz view
  if (selectedModuleId && selectedModule && questions && !questionsLoading) {
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">AI Literacy</h1>
          <p className="mt-1 text-sm text-gray-500">
            Learn about AI safety and responsible use
          </p>
        </div>
        <QuizView
          module={selectedModule}
          questions={questions}
          groupId={groupId || ""}
          memberId={user?.id || ""}
          onBack={() => setSelectedModuleId(null)}
        />
      </div>
    );
  }

  // Loading questions
  if (selectedModuleId && questionsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading quiz...</span>
      </div>
    );
  }

  // Module catalog
  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Literacy</h1>
          <p className="mt-1 text-sm text-gray-500">
            Learn about AI safety and responsible use through interactive quizzes
          </p>
        </div>
        <select
          value={ageFilter || ""}
          onChange={(e) =>
            setAgeFilter(e.target.value ? Number(e.target.value) : undefined)
          }
          aria-label="Filter by age"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="">All ages</option>
          <option value="6">Age 6+</option>
          <option value="8">Age 8+</option>
          <option value="10">Age 10+</option>
          <option value="12">Age 12+</option>
        </select>
      </div>

      {groupId && <ProgressCard memberId={user?.id || ""} />}

      {!modules || modules.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center text-center">
          <BookOpen className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">
            No modules available
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Check back later for new AI literacy content
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((m) => (
            <ModuleCard
              key={m.id}
              module={m}
              onStart={setSelectedModuleId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Page Export (with Suspense for useSearchParams safety) ───────────────────

export default function LiteracyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <LiteracyPageContent />
    </Suspense>
  );
}
