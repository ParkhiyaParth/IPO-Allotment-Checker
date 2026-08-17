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
