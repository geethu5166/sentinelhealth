import React, { useState } from "react";
import { CheckCircle, CheckSquare, Clock, Filter, ShieldCheck } from "lucide-react";
import { useTasks, useUpdateTask } from "../../lib/api/hooks";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { formatTimestamp } from "../../lib/utils";

export const TasksPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data: tasks, isLoading } = useTasks(statusFilter || undefined);
  const updateTaskMutation = useUpdateTask();

  const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);
  const [evidenceText, setEvidenceText] = useState<string>("");

  const handleAcknowledgeTask = async (taskId: string) => {
    await updateTaskMutation.mutateAsync({
      taskId,
      payload: {
        status: "in_progress",
      },
    });
  };

  const handleCompleteTask = async (taskId: string) => {
    if (!evidenceText) return;
    await updateTaskMutation.mutateAsync({
      taskId,
      payload: {
        status: "completed",
        completion_evidence: evidenceText,
      },
    });
    setCompletingTaskId(null);
    setEvidenceText("");
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Preventive Action & Mitigation Tasks</h2>
        <p className="text-muted-foreground text-sm">
          Track assigned playbook tasks, responsible operational roles, completion evidence, and supervisory sign-offs.
        </p>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs border rounded px-3 py-1.5 bg-background"
        >
          <option value="">All Tasks</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {/* Completion Modal / Input Box if active */}
      {completingTaskId && (
        <Card className="border-primary bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Record Completion Evidence for Task</CardTitle>
            <CardDescription className="text-xs">
              Provide verifiable verification evidence (e.g. site inspection log, signed shift roster).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="w-full text-xs p-3 border rounded-md bg-background min-h-[80px]"
              placeholder="e.g. Verified cold water points active in bays 1-4; adjusted outdoor shift to commence at 06:00..."
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
            />
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setCompletingTaskId(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!evidenceText || updateTaskMutation.isPending}
                onClick={() => handleCompleteTask(completingTaskId)}
              >
                Submit Evidence & Complete Task
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tasks Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !tasks || tasks.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <CheckSquare className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No preventive tasks currently open.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Title & Action</TableHead>
                  <TableHead>Accountable Role</TableHead>
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
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                          t.status === "completed"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 border-emerald-300"
                            : t.status === "in_progress"
                            ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200 border-blue-300"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200 border-amber-300"
                        }`}
                      >
                        {t.status === "completed" ? "Completion recorded" : t.status.replace(/_/g, " ")}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold text-xs text-foreground">{t.title}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {t.approval_required ? "• Requires Occupational Health sign-off" : "• Routine operational task"}
                      </div>
                      {t.completion_evidence && (
                        <div className="mt-1.5 text-[11px] font-mono text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 p-1.5 rounded border border-emerald-200 dark:border-emerald-800 flex items-start gap-1.5">
                          <ShieldCheck className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-600" />
                          <span>
                            <strong>Completion recorded:</strong> {t.completion_evidence}
                          </span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="capitalize text-xs text-muted-foreground">
                      {t.assigned_role.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs font-semibold">Tier {t.priority}</span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {t.due_at ? formatTimestamp(t.due_at) : "Immediate"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {t.status === "pending" && (
                          <Button
                            size="sm"
                            variant="secondary"
                            className="text-xs h-7 px-2"
                            disabled={updateTaskMutation.isPending}
                            onClick={() => handleAcknowledgeTask(t.id)}
                          >
                            <Clock className="h-3.5 w-3.5 mr-1 text-blue-600" /> Acknowledge
                          </Button>
                        )}
                        {t.status !== "completed" && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs h-7 px-2"
                            onClick={() => setCompletingTaskId(t.id)}
                          >
                            <CheckCircle className="h-3.5 w-3.5 mr-1 text-emerald-500" /> Complete
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

