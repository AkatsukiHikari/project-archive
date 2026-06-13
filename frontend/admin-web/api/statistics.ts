/**
 * 档案统计 API 层：综合统计 / 大屏驾驶舱 / 年度报表（DA-2 口径）
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 类型定义 ─────────────────────────────────────────────────────────────────

export interface NameValue {
  name: string;
  value: number;
}

export interface StatsKpi {
  holdings_total: number;
  staging_pending: number;
  fonds_count: number;
  year_new: number;
  digitized_count: number;
  digitized_rate: number;
  capacity_gb: number;
  year_util_visits: number;
  opened_count: number;
  open_rate: number;
}

export interface OverviewData {
  kpi: StatsKpi;
  charts: {
    holdings_by_year: NameValue[];
    by_category: NameValue[];
    by_bgqx: NameValue[];
    by_mj: NameValue[];
    by_kfzt: NameValue[];
    by_fonds: NameValue[];
    monthly_new: NameValue[];
    util_by_type: NameValue[];
    util_monthly: NameValue[];
  };
}

export interface CockpitData {
  kpi: StatsKpi;
  dynamic: {
    today_util: number;
    transit_transfers: number;
    active_appraisal_tasks: number;
    detection_pass_rate: number | null;
  };
  charts: {
    holdings_by_year: NameValue[];
    by_category: NameValue[];
    by_kfzt: NameValue[];
    by_fonds: NameValue[];
    util_monthly: NameValue[];
    by_bgqx: NameValue[];
  };
}

export interface IndicatorItem {
  key: string;
  label: string;
  unit: string;
  source: "auto" | "manual";
  hint?: string;
}

export interface IndicatorGroup {
  key: string;
  name: string;
  items: IndicatorItem[];
}

export interface AnnualReport {
  year: number;
  status: "none" | "draft" | "final";
  auto_data: Record<string, number>;
  manual_data: Record<string, number>;
  generated_at: string | null;
  finalized_at: string | null;
  definitions?: IndicatorGroup[];
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const StatisticsAPI = {
  overview: (fondsId?: string) =>
    http.get<ApiResponse<OverviewData>, ApiResponse<OverviewData>>("/statistics/overview", {
      params: fondsId ? { fonds_id: fondsId } : {},
    }),

  cockpit: () =>
    http.get<ApiResponse<CockpitData>, ApiResponse<CockpitData>>("/statistics/cockpit"),

  listAnnualReports: () =>
    http.get<ApiResponse<AnnualReport[]>, ApiResponse<AnnualReport[]>>("/statistics/annual-reports"),

  getAnnualReport: (year: number) =>
    http.get<ApiResponse<AnnualReport>, ApiResponse<AnnualReport>>(`/statistics/annual-reports/${year}`),

  generateAnnualReport: (year: number) =>
    http.post<ApiResponse<AnnualReport>, ApiResponse<AnnualReport>>(`/statistics/annual-reports/${year}/generate`),

  saveAnnualReport: (year: number, manualData: Record<string, number>) =>
    http.put<ApiResponse<AnnualReport>, ApiResponse<AnnualReport>>(`/statistics/annual-reports/${year}`, {
      manual_data: manualData,
    }),

  finalizeAnnualReport: (year: number) =>
    http.post<ApiResponse<AnnualReport>, ApiResponse<AnnualReport>>(`/statistics/annual-reports/${year}/finalize`),

  reopenAnnualReport: (year: number) =>
    http.post<ApiResponse<AnnualReport>, ApiResponse<AnnualReport>>(`/statistics/annual-reports/${year}/reopen`),
};
