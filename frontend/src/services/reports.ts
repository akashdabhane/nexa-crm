import { api } from "@/lib/api-client";
import type { Activity, LeadSource, LeadStatus, Task, UserRole } from "@/types";

export type DateRangeParams = { start_date?: string; end_date?: string };

export interface PipelineRow {
  stage_id: string;
  stage: string;
  count: number;
  value: number;
  weighted_value: number;
}

export interface RevenueRow {
  month: string;
  deals: number;
  revenue: number;
}

export interface LeadSourceRow {
  source: LeadSource;
  leads: number;
  converted: number;
  conversion_rate: number;
  avg_score: number;
}

export interface LeadConversionReport {
  total_leads: number;
  converted: number;
  conversion_rate: number;
  avg_days_to_convert: number | null;
  by_status: { status: LeadStatus; count: number }[];
}

export interface WinLossReport {
  won: number;
  lost: number;
  won_value: number;
  lost_value: number;
  win_rate: number;
  by_month: { month: string; won: number; lost: number; won_value: number; lost_value: number }[];
}

export interface RepPerformanceRow {
  user_id: string;
  name: string;
  role: UserRole;
  deals_won: number;
  revenue: number;
  deals_lost: number;
  win_rate: number;
  open_deals: number;
  open_value: number;
  leads: number;
  leads_converted: number;
  activities: number;
}

export interface DashboardSummary {
  totals: {
    contacts: number;
    companies: number;
    leads: number;
    open_leads: number;
    active_deals: number;
    won_deals: number;
    lost_deals: number;
    pipeline_value: number;
    won_value: number;
    weighted_pipeline_value: number;
    win_rate: number;
    lead_conversion_rate: number;
    converted_leads: number;
  };
  pipeline: PipelineRow[];
  revenue: RevenueRow[];
  lead_sources: LeadSourceRow[];
  recent_activities: Activity[];
  upcoming_tasks: Task[];
}

const get = <T>(path: string, params?: DateRangeParams) => api.get<T>(path, { params }).then((r) => r.data);

export const reportsService = {
  dashboard: () => get<DashboardSummary>("/dashboard/summary"),
  leadConversion: (p: DateRangeParams) => get<LeadConversionReport>("/reports/lead-conversion", p),
  pipeline: (p: DateRangeParams) => get<PipelineRow[]>("/reports/pipeline", p),
  revenue: (p: DateRangeParams) => get<RevenueRow[]>("/reports/revenue", p),
  winLoss: (p: DateRangeParams) => get<WinLossReport>("/reports/win-loss", p),
  repPerformance: (p: DateRangeParams) => get<RepPerformanceRow[]>("/reports/rep-performance", p),
  leadSources: (p: DateRangeParams) => get<LeadSourceRow[]>("/reports/lead-sources", p),
};

/** "2026-03" -> "Mar 2026" */
export function monthLabel(month: string) {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}
