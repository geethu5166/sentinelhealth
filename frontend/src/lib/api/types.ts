export interface UserInfo {
  id: string;
  email: string;
  display_name?: string;
  external_id: string;
  is_active: boolean;
  current_tenant_id?: string;
  current_role?: string;
  memberships: MembershipInfo[];
}

export interface MembershipInfo {
  id: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
  scopes?: Record<string, any>;
  is_active: boolean;
}

export interface SeverityCount {
  severity: string;
  count: number;
}

export interface ActiveEpisode {
  id: string;
  hazard: string;
  severity: string;
  evidence_class: string;
  status: string;
  geography_name: string;
  target_period_start: string;
  target_period_end: string;
  first_detected_at: string;
  contributing_signal_count: number;
}

export interface SourceHealth {
  id: string;
  name: string;
  signal_family: string;
  status: string;
  freshness_minutes: number;
  threshold_minutes: number;
  last_received_at?: string;
}

export interface OverviewData {
  active_alert_count: number;
  severity_breakdown: SeverityCount[];
  pending_task_count: number;
  sources_online_count: number;
  total_sources_count: number;
  last_update_at?: string;
  active_episodes: ActiveEpisode[];
  sources: SourceHealth[];
  data_mode: string;
}

export interface AlertSummary {
  id: string;
  tenant_id: string;
  hazard: string;
  evidence_class: string;
  severity: string;
  status: string;
  geography_id: string;
  geography_name?: string;
  workplace_id?: string;
  workplace_name?: string;
  target_period_start: string;
  target_period_end: string;
  first_detected_at: string;
  latest_revision_at?: string;
  episode_key?: string;
  responsible_role?: string;
  evidence_score?: number;
  suppression_status?: string;
  created_at: string;
}

export interface AlertEvidence {
  id: string;
  signal_family: string;
  source_id?: string;
  metric_code: string;
  observed_value?: number;
  expected_value?: number;
  excess?: number;
  rate_difference?: number;
  standardised_residual?: number;
  prediction_interval_lower?: number;
  prediction_interval_upper?: number;
  ewma_value?: number;
  ewma_threshold?: number;
  baseline_period_start?: string;
  baseline_period_end?: string;
  source_freshness_minutes?: number;
  data_label: string;
  model_type?: string;
  model_version?: string;
  is_suppressed: boolean;
}

export interface AlertDetail extends AlertSummary {
  evidence_score_components?: Record<string, any>;
  suppression_reason?: string;
  playbook_id?: string;
  privacy_policy_version?: string;
  evidences: AlertEvidence[];
  state_events: Array<{
    id: string;
    from_status?: string;
    to_status: string;
    actor_id?: string;
    reason?: string;
    created_at: string;
  }>;
  recommended_action?: string;
  recommendation_assumptions?: Record<string, any>;
}

export interface TaskSummary {
  id: string;
  tenant_id: string;
  alert_id: string;
  title: string;
  assigned_role: string;
  assigned_to_user_id?: string;
  status: string;
  priority: number;
  due_at?: string;
  completed_at?: string;
  completion_evidence?: string;
  approval_required: boolean;
  created_at: string;
}

export interface SignalRecord {
  id: string;
  tenant_id: string;
  source_id: string;
  metric_code: string;
  signal_family: string;
  value?: number;
  unit: string;
  numerator?: number;
  denominator?: number;
  denominator_unit?: string;
  contributor_count?: number;
  period_start: string;
  period_end: string;
  observed_at: string;
  source_available_at: string;
  geography_id?: string;
  workplace_id?: string;
  location_basis: string;
  location_confidence: string;
  data_label: string;
  is_suppressed: boolean;
  suppression_reason?: string;
}

export interface GeographyInfo {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  level: string;
  population_estimate?: number;
  is_active: boolean;
}

export interface MapLayerFeature {
  type: "Feature";
  geometry?: any;
  properties: {
    geography_id: string;
    geography_code: string;
    geography_name: string;
    status: "elevated" | "valid_non_elevated" | "suppressed" | "insufficient_data" | "unavailable";
    metric_code: string;
    period?: string;
    value?: number | null;
    unit?: string | null;
    is_suppressed: boolean;
    suppression_reason?: string | null;
    encounter_rate_per_100k?: number | null;
    rate_label?: string;
    location_confidence?: string;
    location_basis?: string;
  };
}

export interface MapLayerCollection {
  type: "FeatureCollection";
  metric_code: string;
  features: MapLayerFeature[];
}

