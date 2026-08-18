export type AllotmentStatus = 'ALLOTTED' | 'NOT_ALLOTTED' | 'NOT_APPLIED' | 'CHECK_FAILED';

export interface IPOSummary {
  id: string;
  company_name: string;
  registrar: string;
  allotment_date: string;
  listing_date: string | null;
  automation_supported: boolean;
}

export interface RecentIposResponse {
  ipos: IPOSummary[];
  generated_at: string;
}

export interface AllotmentResultItem {
  pan: string;
  label: string;
  status: AllotmentStatus;
  shares_allotted: number | null;
  manual_check_url: string | null;
  message: string | null;
}

export interface CheckAllotmentResponse {
  ipo_id: string;
  results: AllotmentResultItem[];
  checked_at: string;
}

export type IPOCatalogStatus = 'open' | 'upcoming' | 'closed';

export interface SubscriptionCategory {
  offered: number | null;
  applied: number | null;
  times: number | null;
}

export type ProfitBasis = 'actual' | 'estimated';
export type ApplySignal = 'strong_apply' | 'consider' | 'skip';

export interface IPOCatalogSummary {
  id: string;
  company_name: string;
  status: IPOCatalogStatus;
  open_date: string | null;
  close_date: string | null;
  price_band_low: number | null;
  price_band_high: number | null;
  issue_price: number | null;
  lot_size: number | null;
  issue_size_cr: number | null;
  gmp_value: number | null;
  gmp_percent: number | null;
  listing_price: number | null;
  current_price: number | null;
  linked_registrar_ipo_id: string | null;
  profit_per_lot: number | null;
  profit_basis: ProfitBasis | null;
  apply_signal: ApplySignal | null;
  apply_signal_reason: string | null;
}

export interface IPOCatalogDetail extends IPOCatalogSummary {
  listing_date: string | null;
  gmp_updated_at: string | null;
  subscription_qib: SubscriptionCategory;
  subscription_hni: SubscriptionCategory;
  subscription_retail: SubscriptionCategory;
}

export interface IPOCatalogListResponse {
  ipos: IPOCatalogSummary[];
  generated_at: string;
}
