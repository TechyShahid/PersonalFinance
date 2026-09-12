/**
 * API Client — Centralized fetch wrapper for backend communication.
 */

const API_BASE = 'http://localhost:8000/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Dashboard ──────────────────────────────────────────────────────────────────

export const dashboardAPI = {
  getSummary: () => fetchAPI<DashboardSummary>('/dashboard/summary'),
  getPerformance: (days = 90) => fetchAPI<PerformanceResponse>(`/dashboard/performance?days=${days}`),
  getFiiDii: (days = 10) => fetchAPI<FiiDiiEntry[]>(`/dashboard/fii-dii?days=${days}`),
};

// ─── Screener ───────────────────────────────────────────────────────────────────

export const screenerAPI = {
  getCandidates: (params?: { min_score?: number; setup_type?: string; cap_category?: string; sort_by?: string }) => {
    const query = new URLSearchParams();
    if (params?.min_score) query.set('min_score', String(params.min_score));
    if (params?.setup_type) query.set('setup_type', params.setup_type);
    if (params?.cap_category) query.set('cap_category', params.cap_category);
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    return fetchAPI<ScreeningCandidate[]>(`/screener/candidates?${query}`);
  },
  getSparkline: (symbol: string, days = 20) =>
    fetchAPI<SparklineData[]>(`/screener/sparkline/${symbol}?days=${days}`),
  runScan: () => fetchAPI<ScreeningCandidate[]>('/screener/run', { method: 'POST' }),
};

// ─── Portfolio ──────────────────────────────────────────────────────────────────

export const portfolioAPI = {
  getPortfolios: () => fetchAPI<Portfolio[]>('/portfolio/'),
  getHoldings: (type?: string) => {
    const query = type ? `?portfolio_type=${type}` : '';
    return fetchAPI<Holding[]>(`/portfolio/holdings/all${query}`);
  },
  getActiveOrders: () => fetchAPI<TradeOrder[]>('/portfolio/orders/active'),
  executeTrade: (trade: TradeOrderCreate) =>
    fetchAPI<TradeOrder>('/portfolio/trade', { method: 'POST', body: JSON.stringify(trade) }),
};

// ─── Calculator ─────────────────────────────────────────────────────────────────

export const calculatorAPI = {
  positionSize: (req: PositionSizeRequest) =>
    fetchAPI<PositionSizeResponse>('/calculator/position-size', {
      method: 'POST', body: JSON.stringify(req),
    }),
  taxEstimate: (req: TaxEstimateRequest) =>
    fetchAPI<TaxEstimateResponse>('/calculator/tax-estimate', {
      method: 'POST', body: JSON.stringify(req),
    }),
};

// ─── Journal ────────────────────────────────────────────────────────────────────

export const journalAPI = {
  getTrades: (limit = 50) => fetchAPI<TradeOrder[]>(`/journal/trades?limit=${limit}`),
  getStats: () => fetchAPI<JournalStats>('/journal/stats'),
};

// ─── Symbols ────────────────────────────────────────────────────────────────────

export const symbolsAPI = {
  getAll: () => fetchAPI<{ symbols: string[]; count: number }>('/symbols'),
};

// ─── Type Definitions ───────────────────────────────────────────────────────────

export interface DashboardSummary {
  total_capital: number;
  core_deployed: number;
  core_cash: number;
  satellite_deployed: number;
  satellite_cash: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  active_swing_trades: number;
  max_concurrent_swings: number;
  todays_pnl: number;
  win_rate: number;
  total_trades: number;
}

export interface PerformancePoint {
  date: string;
  portfolio_value: number;
  nifty_50_value: number;
  nifty_midcap_150_value: number;
}

export interface PerformanceResponse {
  data: PerformancePoint[];
  portfolio_return_pct: number;
  nifty_50_return_pct: number;
  nifty_midcap_return_pct: number;
}

export interface FiiDiiEntry {
  trade_date: string;
  fii_net: number;
  dii_net: number;
  fii_buy: number;
  fii_sell: number;
  dii_buy: number;
  dii_sell: number;
}

export interface ScreeningCandidate {
  id: number;
  symbol: string;
  scan_date: string;
  composite_score: number;
  setup_type: string;
  delivery_pct: number | null;
  turnover_cr: number | null;
  risk_reward_ratio: number | null;
  entry_price: number | null;
  stop_loss: number | null;
  target_price: number | null;
  rationale: string | null;
  cap_category?: string;
  market_cap_cr?: number;
  sector?: string;
  is_active: boolean;
}

export interface SparklineData {
  symbol: string;
  trade_date: string;
  close_price: number;
  high_price: number;
  low_price: number;
  open_price: number;
}

export interface Portfolio {
  id: number;
  user_id: number;
  portfolio_type: string;
  deployed_capital: number;
  cash_available: number;
  created_at: string;
}

export interface Holding {
  id: number;
  portfolio_id: number;
  symbol: string;
  exchange: string;
  quantity: number;
  avg_buy_price: number;
  buy_date: string;
  status: string;
  current_price: number | null;
  unrealized_pnl: number | null;
  stop_loss_price: number | null;
  target_price: number | null;
}

export interface TradeOrder {
  id: number;
  user_id: number;
  portfolio_id: number;
  symbol: string;
  order_type: string;
  status: string;
  quantity: number;
  entry_price: number;
  stop_loss: number | null;
  target_price: number | null;
  exit_price: number | null;
  entry_date: string;
  exit_date: string | null;
  realized_pnl: number | null;
  stt_paid: number | null;
  gst_paid: number | null;
  sebi_fee: number | null;
  brokerage: number | null;
  stamp_duty: number | null;
  exchange_txn_charge: number | null;
  tax_liability: number | null;
  tax_type: string | null;
  net_return: number | null;
  notes: string | null;
}

export interface TradeOrderCreate {
  symbol: string;
  order_type: 'BUY' | 'SELL';
  quantity: number;
  entry_price: number;
  stop_loss?: number;
  target_price?: number;
  portfolio_type?: string;
  notes?: string;
}

export interface PositionSizeRequest {
  symbol: string;
  entry_price: number;
  stop_loss_price: number;
  portfolio_capital?: number;
  risk_pct?: number;
}

export interface PositionSizeResponse {
  symbol: string;
  entry_price: number;
  stop_loss_price: number;
  risk_per_share: number;
  shares_to_buy: number;
  total_investment: number;
  risk_amount: number;
  risk_pct_of_portfolio: number;
  target_price_2r: number;
  potential_profit: number;
  estimated_costs: Record<string, unknown>;
  net_pnl_at_target: number;
}

export interface TaxEstimateRequest {
  buy_price: number;
  sell_price: number;
  quantity: number;
  holding_days: number;
  brokerage_per_order?: number;
}

export interface TaxEstimateResponse {
  gross_pnl: number;
  stt: number;
  exchange_txn_charge: number;
  sebi_fee: number;
  gst: number;
  stamp_duty: number;
  brokerage: number;
  total_transaction_costs: number;
  tax_type: string;
  taxable_gain: number;
  tax_amount: number;
  net_pnl: number;
  effective_return_pct: number;
}

export interface JournalStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_win_amount: number;
  avg_loss_amount: number;
  avg_hold_days: number;
  avg_r_multiple: number;
  max_drawdown: number;
  total_net_pnl: number;
  total_tax_paid: number;
  expectancy: number;
  stcg_total: number;
  ltcg_total: number;
  ltcg_exemption_used: number;
  ltcg_exemption_remaining: number;
}
