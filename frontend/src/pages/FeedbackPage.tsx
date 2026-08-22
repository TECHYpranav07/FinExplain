import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel, ErrorState } from "@/components/finex/primitives";

export function FeedbackPage() {
  const [queryText, setQueryText] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [isCorrect, setIsCorrect] = useState(true);
  const [correction, setCorrection] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const feedbackMutation = useMutation({
    mutationFn: async () => {
      return api.submitFeedback({
        query: queryText,
        answer: answerText,
        is_correct: isCorrect,
        correction: correction || undefined,
      });
    },
    onSuccess: () => {
      setSubmitted(true);
      setQueryText("");
      setAnswerText("");
      setCorrection("");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim() || !answerText.trim()) return;
    feedbackMutation.mutate();
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Evaluation & Continuous Learning"
        title="Model Feedback & Grounding Audit"
        description="Provide corrective feedback on AI extractions to improve hallucination prevention and citation accuracy."
      />

      <Panel title="Submit Analysis Feedback">
        {submitted ? (
          <div className="py-8 text-center space-y-3">
            <i className="fa-solid fa-circle-check text-3xl text-success" />
            <h3 className="text-base font-semibold text-white">Feedback Submitted Successfully</h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Your feedback has been logged in Supabase to enhance future retrieval and citation scoring.
            </p>
            <button
              type="button"
              onClick={() => setSubmitted(false)}
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90"
            >
              Submit Another Entry
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Target User Query / Question <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. What is the prepayment penalty after 12 months?"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                AI Generated Answer / Extraction <span className="text-danger">*</span>
              </label>
              <textarea
                rows={3}
                required
                placeholder="Paste the answer that was generated..."
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Was the answer factually grounded in the contract?
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
                  <input
                    type="radio"
                    name="isCorrect"
                    checked={isCorrect}
                    onChange={() => setIsCorrect(true)}
                    className="text-white"
                  />
                  <span>Yes, factually accurate</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
                  <input
                    type="radio"
                    name="isCorrect"
                    checked={!isCorrect}
                    onChange={() => setIsCorrect(false)}
                    className="text-white"
                  />
                  <span>No, contains errors / missed clauses</span>
                </label>
              </div>
            </div>

            {!isCorrect && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Ground Truth / Verified Correction
                </label>
                <textarea
                  rows={3}
                  placeholder="Explain what the actual document clause states and where..."
                  value={correction}
                  onChange={(e) => setCorrection(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white focus:outline-none"
                />
              </div>
            )}

            {feedbackMutation.isError && (
              <ErrorState message={(feedbackMutation.error as any)?.message || "Failed to submit"} />
            )}

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={feedbackMutation.isPending || !queryText.trim() || !answerText.trim()}
                className="rounded-lg bg-white px-5 py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40"
              >
                {feedbackMutation.isPending ? "Submitting..." : "Submit Feedback"}
              </button>
            </div>
          </form>
        )}
      </Panel>
    </div>
  );
}
