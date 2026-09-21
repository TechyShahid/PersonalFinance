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

export const midSmallScannerAPI = {
  getSwingCandidates: (params?: {
    cap_type?: string;
    setup?: string;
    min_turnover_cr?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.cap_type) query.set('cap_type', params.cap_type);
    if (params?.setup) query.set('setup', params.setup);
    if (params?.min_turnover_cr !== undefined) query.set('min_turnover_cr', String(params.min_turnover_cr));
    return fetchAPI<MidSmallSwingCandidate[]>(`/v1/scanner/mid-small-swing?${query}`);
  },
};

export const pennyScannerAPI = {
  getPennyCandidates: (params?: {
    exchange?: string;
    setup?: string;
    min_turnover_cr?: number;
    max_operator_risk?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.exchange) query.set('exchange', params.exchange);
    if (params?.setup) query.set('setup', params.setup);
    if (params?.min_turnover_cr !== undefined) query.set('min_turnover_cr', String(params.min_turnover_cr));
    if (params?.max_operator_risk !== undefined) query.set('max_operator_risk', String(params.max_operator_risk));
    return fetchAPI<PennySwingCandidate[]>(`/v1/scanner/penny-swing?${query}`);
  },
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

// ─── Stocks & Historical Candles ────────────────────────────────────────────────

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema20?: number | null;
  ema50?: number | null;
  rsi?: number | null;
}

export interface StockCandlesSummary {
  current_price: number;
  previous_close: number;
  change_pct: number;
  period_return_pct: number;
  high_period: number;
  low_period: number;
  latest_volume: number;
  candle_count: number;
  ticker_used: string;
}

export interface StockCandlesResponse {
  symbol: string;
  exchange: string;
  period: string;
  summary: StockCandlesSummary;
  candles: CandleData[];
}

export const stocksAPI = {
  getCandles: (symbol: string, params?: { exchange?: string; period?: string; interval?: string; refresh?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.exchange) query.set('exchange', params.exchange);
    if (params?.period) query.set('period', params.period);
    if (params?.interval) query.set('interval', params.interval);
    if (params?.refresh) query.set('refresh', 'true');
    return fetchAPI<StockCandlesResponse>(`/stocks/${encodeURIComponent(symbol)}/candles?${query}`);
  },
};

// ─── New Listings & IPO Tracker ─────────────────────────────────────────────────

export const newListingsAPI = {
  getAll: (params?: {
    search?: string;
    category?: string;
    timeframe_days?: number;
    min_return?: number;
    only_fresh_ipos?: boolean;
    listing_type?: string;
    op_profit_growing?: boolean;
    min_op_profit_growth?: number;
    sort_by?: string;
    order?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.category) query.set('category', params.category);
    if (params?.timeframe_days) query.set('timeframe_days', String(params.timeframe_days));
    if (params?.min_return !== undefined) query.set('min_return', String(params.min_return));
    if (params?.only_fresh_ipos !== undefined) query.set('only_fresh_ipos', String(params.only_fresh_ipos));
    if (params?.listing_type) query.set('listing_type', params.listing_type);
    if (params?.op_profit_growing !== undefined) query.set('op_profit_growing', String(params.op_profit_growing));
    if (params?.min_op_profit_growth !== undefined) query.set('min_op_profit_growth', String(params.min_op_profit_growth));
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    if (params?.order) query.set('order', params.order);
    if (params?.page) query.set('page', String(params.page));
    if (params?.limit) query.set('limit', String(params.limit));
    return fetchAPI<NewListingsListResponse>(`/new-listings?${query}`);
  },
  getOutperformers: (params?: { tier?: string; include_relisted?: boolean; op_profit_growing?: boolean; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.tier) query.set('tier', params.tier);
    if (params?.include_relisted !== undefined) query.set('include_relisted', String(params.include_relisted));
    if (params?.op_profit_growing !== undefined) query.set('op_profit_growing', String(params.op_profit_growing));
    if (params?.limit) query.set('limit', String(params.limit));
    return fetchAPI<NewlyListedStock[]>(`/new-listings/outperformers?${query}`);
  },
  getStats: () => fetchAPI<NewListingsStats>('/new-listings/stats'),
  refresh: () => fetchAPI<{ status: string; total_listings: number; outperformers_count: number }>('/new-listings/refresh', { method: 'POST' }),
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

export interface MidSmallSwingCandidate {
  symbol: string;
  company_name: string;
  market_cap_tier: string;
  market_cap_cr: number;
  sector: string;
  setup_type: string;
  composite_score: number;
  delivery_multiple: number;
  delivery_pct: number;
  deliverable_value_cr: number;
  turnover_cr: number;
  adv_20d: number;
  relative_strength_score: number;
  rs_benchmark: string;
  pivot_price: number;
  entry_price: number;
  suggested_stop_loss: number;
  target_price: number;
  risk_reward_ratio: number;
  asm_gsm_stage: number;
  rationale: string;
}

export interface PennySwingCandidate {
  symbol: string;
  company_name: string;
  exchange: string;              // NSE | BSE
  market_cap_cr: number;
  sector: string;
  price_band_pct: number;        // 10.0 | 20.0
  circuit_status: string;
  setup_type: string;
  composite_score: number;
  operator_risk_score: number;   // 0 - 100
  risk_classification: string;   // LOW_RISK | MODERATE | ELEVATED
  entry_price: number;
  suggested_stop_loss: number;
  target_price: number;
  risk_reward_ratio: number;
  volume_surge_multiple: number;
  delivery_pct: number;
  deliverable_value_cr: number;
  turnover_cr: number;
  trade_count: number;
  bid_ask_spread_pct: number;
  max_safe_shares: number;
  max_safe_capital: number;
  capital_pct: number;
  circuit_warning: string;
  rationale: string;
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

export interface NewlyListedStock {
  id: number;
  symbol: string;
  company_name: string;
  series: string;
  listing_date: string;
  days_since_listing: number;
  category?: string;
  market_cap_cr?: number;
  listing_price?: number;
  current_price?: number;
  change_pct?: number;
  return_since_listing_pct?: number;
  all_time_high?: number;
  drawdown_from_high_pct?: number;
  volume?: number;
  turnover_cr?: number;
  delivery_pct?: number;
  performance_rank?: number;
  is_outperformer: boolean;
  is_relisted: boolean;
  listing_type?: 'FRESH_IPO' | 'RE_LISTED';
  performance_tier?: 'MULTIBAGGER' | 'HIGH_FLYER' | 'OUTPERFORMER' | 'NEUTRAL' | 'LAGGARD';
  operating_profit_cr?: number | null;
  prev_operating_profit_cr?: number | null;
  operating_profit_growth_pct?: number | null;
  is_op_profit_growing?: boolean;
}

export interface NewListingsListResponse {
  items: NewlyListedStock[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface NewListingsStats {
  total_listings: number;
  fresh_ipos_count: number;
  relisted_count: number;
  outperformers_count: number;
  outperformers_pct: number;
  median_return_pct: number;
  average_return_pct: number;
  op_profit_growing_count?: number;
  op_profit_growing_pct?: number;
  top_performer?: {
    symbol: string;
    company_name: string;
    return_pct: number;
    current_price?: number;
    listing_date?: string;
  };
  category_breakdown: Record<string, number>;
}


