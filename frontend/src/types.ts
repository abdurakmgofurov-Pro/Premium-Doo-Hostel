// Shared types for the Flask app's client-side pages.
//
// `window.T`/`LANG`/`CSRF_TOKEN`/`DISPLAY_CURRENCY` are set once by an
// inline <script> in templates/base.html (before this bundle loads) from
// server-side Jinja values; each page may set a few more of its own
// (declared where used). Everything here mirrors real server response
// shapes (aggregate.py / db.py) -- kept in one place so every page ports
// against the same types instead of re-guessing field names.

export {};

declare global {
  interface Window {
    T: Record<string, string>;
    LANG: "ru" | "en" | "uz";
    CSRF_TOKEN: string;
    DISPLAY_CURRENCY: "UZS" | "USD";
  }
}

export interface CurrencyAmounts {
  UZS: number;
  USD: number;
}

export interface ChannelStat {
  count: number;
  revenue: Partial<CurrencyAmounts>;
  currency: "UZS" | "USD";
}

export interface RoomTypeStat extends ChannelStat {
  avg_nights: number;
}

export interface StayStats {
  avg_nights: number;
  avg_adults: number;
  solo_count: number;
  group_count: number;
  with_children_count: number;
}

/** Return shape of aggregate.py's `aggregate_bookings()`. */
export interface AggregateData {
  total_bookings: number;
  active_count: number;
  cancelled_count: number;
  cancellation_rate: number;
  revenue_by_currency: Partial<CurrencyAmounts>;
  prepaid_by_currency: Partial<CurrencyAmounts>;
  count_by_currency: Partial<CurrencyAmounts>;
  cancelled_value_by_currency: Partial<CurrencyAmounts>;
  by_channel: Record<string, ChannelStat>;
  by_month: Record<string, Partial<CurrencyAmounts>>;
  count_month: Record<string, Partial<CurrencyAmounts>>;
  by_room_type: Record<string, RoomTypeStat>;
  by_rate_plan: Record<string, ChannelStat>;
  by_payment_method: Record<string, ChannelStat>;
  stay_stats: StayStats;
  rows: unknown[];
}

/** Return shape of db.py's `summarize_transactions()`. */
export interface ManualSummary {
  income: CurrencyAmounts;
  expense: CurrencyAmounts;
  unpaid_expense: CurrencyAmounts;
  unpaid_income: CurrencyAmounts;
  revenue_extra: CurrencyAmounts;
  by_category: Record<string, Partial<CurrencyAmounts>>;
  by_group: Record<string, CurrencyAmounts>;
}

/** Return shape of app.py's `real_cash_totals()` — real Kassa+Bank cash
 * movement for the period (same source as Forma 3), as opposed to
 * `AggregateData.revenue_by_currency`, which is Exely's accrual booking
 * price and may not have been collected as real money yet. */
export interface RealCashTotals {
  income: CurrencyAmounts;
  expense: CurrencyAmounts;
}

export type SyncStatus = "loading" | "ok" | "error";

export interface SyncProgress {
  done: number;
  total: number;
}

/** JSON body returned by GET /api/data. */
export interface ApiDataPayload {
  status: SyncStatus;
  error: string | null;
  last_attempt: string | null;
  last_success: string | null;
  progress: SyncProgress | null;
  data: AggregateData | null;
  manual: ManualSummary;
  real_cash: RealCashTotals;
}
