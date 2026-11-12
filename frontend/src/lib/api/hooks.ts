import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import {
  AlertDetail,
  AlertEvidence,
  AlertSummary,
  GeographyInfo,
  OverviewData,
  SignalRecord,
  TaskSummary,
  UserInfo,
} from "./types";

export function useOverview() {
  return useQuery<OverviewData>({
    queryKey: ["overview"],
    queryFn: () => apiFetch<OverviewData>("/overview"),
    refetchInterval: 30000,
  });
}

export function useAlerts(filters?: { hazard?: string; severity?: string; status?: string; geography_id?: string }) {
  const params = new URLSearchParams();
  if (filters?.hazard) params.set("hazard", filters.hazard);
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.geography_id) params.set("geography_id", filters.geography_id);

  return useQuery<AlertSummary[]>({
    queryKey: ["alerts", filters],
    queryFn: () => apiFetch<AlertSummary[]>(`/alerts?${params.toString()}`),
  });
}

export function useAlert(id?: string) {
  return useQuery<AlertDetail>({
    queryKey: ["alert", id],
    queryFn: () => apiFetch<AlertDetail>(`/alerts/${id}`),
    enabled: !!id,
  });
}

export function useAlertEvidence(id?: string) {
  return useQuery<AlertEvidence[]>({
    queryKey: ["alert-evidence", id],
    queryFn: () => apiFetch<AlertEvidence[]>(`/alerts/${id}/evidence`),
    enabled: !!id,
  });
}

export function useSignals(filters?: { metric_code?: string; geography_id?: string }) {
  const params = new URLSearchParams();
  if (filters?.metric_code) params.set("metric_code", filters.metric_code);
  if (filters?.geography_id) params.set("geography_id", filters.geography_id);

  return useQuery<SignalRecord[]>({
    queryKey: ["signals", filters],
    queryFn: () => apiFetch<SignalRecord[]>(`/signals?${params.toString()}`),
  });
}

export function useGeographies() {
  return useQuery<GeographyInfo[]>({
    queryKey: ["geographies"],
    queryFn: () => apiFetch<GeographyInfo[]>("/geographies"),
  });
}

export function useTasks(statusFilter?: string) {
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);

  return useQuery<TaskSummary[]>({
    queryKey: ["tasks", statusFilter],
    queryFn: () => apiFetch<TaskSummary[]>(`/tasks?${params.toString()}`),
  });
}

export function useTransitionAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, to_status, reason }: { alertId: string; to_status: string; reason: string }) =>
      apiFetch<AlertSummary>(`/alerts/${alertId}/transitions`, {
        method: "POST",
        body: JSON.stringify({ to_status, reason }),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alert", variables.alertId] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: any }) =>
      apiFetch<any>(`/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export interface RealtimeTrainReport {
  status: string;
  latitude: number;
  longitude: number;
  metric_code: string;
  sample_size: number;
  trained_at: string;
  selected_model: string;
  expected_value: number;
  standard_error: number;
  selection_metric: string;
  selection_score: number;
  ewma_anomaly: boolean;
  cusum_anomaly: boolean;
  latest_observed: number;
  provenance: string;
  evidence_label: string;
  candidate_models?: Array<{
    model_type: string;
    expected_value: number;
    standard_error: number;
  }>;
}

export function useTrainRealtimeBaselines() {
  return useMutation({
    mutationFn: (params?: { latitude?: number; longitude?: number; lookback_days?: number }) => {
      const qs = new URLSearchParams();
      if (params?.latitude != null) qs.set("latitude", String(params.latitude));
      if (params?.longitude != null) qs.set("longitude", String(params.longitude));
      if (params?.lookback_days != null) qs.set("lookback_days", String(params.lookback_days));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return apiFetch<RealtimeTrainReport>(`/analytics/train/realtime${suffix}`, { method: "POST" });
    },
  });
}

export function useDetectors() {
  return useQuery<{
    evidence_label: string;
    baselines: string[];
    detectors: Array<{ name: string; role: string }>;
    realtime_source: string;
  }>({
    queryKey: ["analytics-detectors"],
    queryFn: () => apiFetch("/analytics/detectors"),
    staleTime: 60_000,
  });
}

