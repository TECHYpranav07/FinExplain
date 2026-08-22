import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel, Badge, EmptyState, ErrorState } from "@/components/finex/primitives";

interface HITLTask {
  id: string;
  type: string;
  document: string;
  conflict: string;
  status: "pending" | "resolved";
  priority: "HIGH" | "MEDIUM" | "LOW";
  created_at: string;
}

const INITIAL_TASKS: HITLTask[] = [
  {
    id: "task_01",
    type: "conflict_resolution",
    document: "Term_Loan_Master_Agreement_2024.pdf",
    conflict: "Section 4.1 specifies 8.5% fixed interest, while Addendum B references Repo Rate + 2.75% floating.",
    status: "pending",
    priority: "HIGH",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "task_02",
    type: "missing_clause_verification",
    document: "HDFC_Sanction_Letter.pdf",
    conflict: "Prepayment penalty schedule not explicitly found on page 3. Requires confirmation.",
    status: "pending",
    priority: "MEDIUM",
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
];

export function HITLPage() {
  const [tasks, setTasks] = useState<HITLTask[]>(INITIAL_TASKS);
  const [selectedTask, setSelectedTask] = useState<HITLTask | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");
  const [resolvedValue, setResolvedValue] = useState("apply_addendum");

  const resolveMutation = useMutation({
    mutationFn: async ({ taskId, data }: { taskId: string; data: any }) => {
      return api.resolveHitlTask(taskId, data);
    },
    onSuccess: (_, vars) => {
      setTasks((prev) =>
        prev.map((t) => (t.id === vars.taskId ? { ...t, status: "resolved" as const } : t))
      );
      setSelectedTask(null);
      setResolutionNote("");
    },
  });

  const handleResolve = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    resolveMutation.mutate({
      taskId: selectedTask.id,
      data: {
        decision: resolvedValue,
        notes: resolutionNote,
        resolved_at: new Date().toISOString(),
      },
    });
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Operations & Oversight"
        title="Human-In-The-Loop (HITL) Queue"
        description="Audit queue for conflicting document clauses, low-confidence extractions, and critical human sign-offs."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Task List (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Panel
            title="Review Tasks"
            subtitle={`${tasks.filter((t) => t.status === "pending").length} pending items`}
          >
            {tasks.length === 0 ? (
              <EmptyState
                icon="fa-solid fa-user-check"
                title="All caught up!"
                description="No pending HITL audit tasks require human intervention."
              />
            ) : (
              <div className="divide-y divide-white/5">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-4 rounded-lg cursor-pointer transition-all ${
                      selectedTask?.id === task.id
                        ? "bg-surface-3 border border-white/20"
                        : "hover:bg-surface-2/60 border border-transparent"
                    }`}
                    onClick={() => setSelectedTask(task)}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-white">{task.document}</span>
                      <div className="flex items-center gap-2">
                        <Badge tone={task.priority === "HIGH" ? "danger" : "warning"}>
                          {task.priority}
                        </Badge>
                        <Badge tone={task.status === "resolved" ? "success" : "neutral"}>
                          {task.status}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                      {task.conflict}
                    </p>
                    <div className="mt-2 text-[10px] text-muted-foreground/60">
                      Created: {new Date(task.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        {/* Task Detail & Resolution Form (5 cols) */}
        <div className="lg:col-span-5">
          <Panel title="Task Resolution Workspace">
            {!selectedTask ? (
              <EmptyState
                icon="fa-solid fa-magnifying-glass"
                title="Select a task"
                description="Click any task from the queue to view conflict details and record manual human sign-off."
              />
            ) : (
              <form onSubmit={handleResolve} className="space-y-4">
                <div className="rounded-lg border border-white/10 bg-surface-2 p-3 text-xs space-y-2">
                  <div className="text-muted-foreground uppercase text-[10px] tracking-wider">
                    Conflict Description
                  </div>
                  <p className="text-white leading-relaxed">{selectedTask.conflict}</p>
                </div>

                {selectedTask.status === "resolved" ? (
                  <div className="rounded-lg border border-success/30 bg-success/10 p-3 text-xs text-success flex items-center gap-2">
                    <i className="fa-solid fa-circle-check" />
                    <span>This task has been resolved and audit-logged.</span>
                  </div>
                ) : (
                  <>
                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Resolution Decision
                      </label>
                      <select
                        aria-label="Resolution Decision"
                        value={resolvedValue}
                        onChange={(e) => setResolvedValue(e.target.value)}
                        className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:outline-none"
                      >
                        <option value="apply_addendum">Apply Addendum Terms (Overrides Base)</option>
                        <option value="apply_base">Apply Base Master Agreement</option>
                        <option value="request_clarification">Request Official Lender Addendum</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Auditor Notes & Justification
                      </label>
                      <textarea
                        aria-label="Auditor Notes & Justification"
                        rows={3}
                        required
                        placeholder="Document your verification rationale..."
                        value={resolutionNote}
                        onChange={(e) => setResolutionNote(e.target.value)}
                        className="w-full rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white focus:outline-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={resolveMutation.isPending || !resolutionNote.trim()}
                      className="w-full rounded-lg bg-white py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40"
                    >
                      {resolveMutation.isPending ? "Recording Sign-off..." : "Resolve & Sign-off Task"}
                    </button>
                  </>
                )}
              </form>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
