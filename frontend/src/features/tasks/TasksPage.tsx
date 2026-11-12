import React, { useState } from "react";
import { CheckCircle, CheckSquare, Filter } from "lucide-react";
import { useTasks, useUpdateTask } from "../../lib/api/hooks";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { PageHeader } from "../../components/ui/page-header";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

export const TasksPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState("");
  const { data: tasks, isLoading, error, refetch } = useTasks(statusFilter || undefined);
  const updateTaskMutation = useUpdateTask();

  const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);
  const [evidenceText, setEvidenceText] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const handleCompleteTask = async (taskId: string) => {
    if (!evidenceText) return;
    setActionError(null);
    try {
      await updateTaskMutation.mutateAsync({
        taskId,
        payload: {
          status: "completed",
          completion_evidence: evidenceText,
        },
      });
      setCompletingTaskId(null);
      setEvidenceText("");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to complete task.");
    }
  };

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Mitigation tasks"
        description="Track assigned playbook tasks, responsible roles, completion evidence, and supervisory sign-offs."
      />

      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" aria-hidden />
        <label className="text-xs text-muted-foreground">
          <span className="sr-only">Task status</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border bg-background px-3 py-1.5 text-xs text-foreground"
          >
            <option value="">All tasks</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
          </select>
        </label>
      </div>

      {actionError ? (
        <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {actionError}
        </div>
      ) : null}

      {completingTaskId ? (
        <Card className="border-primary bg-primary/5 shadow-panel">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Record completion evidence</CardTitle>
            <CardDescription className="text-xs">
              Provide verifiable verification evidence (e.g. site inspection log, signed shift roster).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="sr-only" htmlFor="task-evidence">
              Completion evidence
            </label>
            <textarea
              id="task-evidence"
              className="min-h-[80px] w-full rounded-md border bg-background p-3 text-xs"
              placeholder="e.g. Verified cold water points active in bays 1-4; adjusted outdoor shift to commence at 06:00..."
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setCompletingTaskId(null);
                  setEvidenceText("");
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!evidenceText || updateTaskMutation.isPending}
                onClick={() => handleCompleteTask(completingTaskId)}
              >
                Submit evidence & complete
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card className="shadow-panel overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4">
              <ErrorState
                title="Tasks unavailable"
                description="Could not load mitigation tasks from the API."
                onRetry={() => refetch()}
              />
            </div>
          ) : !tasks || tasks.length === 0 ? (
            <EmptyState
              icon={CheckSquare}
              title="No preventive tasks open"
              description="Assigned playbook actions will appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Title & action</TableHead>
                    <TableHead>Accountable role</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Deadline</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell>
                        <span
                          className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${
                            t.status === "completed"
                              ? "border-emerald-300 bg-emerald-100 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                              : "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
                          }`}
                        >
                          {humanizeKey(t.status)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs font-semibold">{t.title}</div>
                        <div className="text-[11px] text-muted-foreground">
                          {t.approval_required
                            ? "· Requires occupational health sign-off"
                            : "· Routine operational task"}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs capitalize text-muted-foreground">
                        {humanizeKey(t.assigned_role)}
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs font-semibold">Tier {t.priority}</span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {t.due_at ? formatTimestamp(t.due_at) : "Immediate"}
                      </TableCell>
                      <TableCell className="text-right">
                        {t.status !== "completed" ? (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => setCompletingTaskId(t.id)}
                          >
                            <CheckCircle className="mr-1 h-3.5 w-3.5 text-emerald-600" /> Complete
                          </Button>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
