import { useState, useEffect } from 'react';
import { newListingsAPI, type NewlyListedStock, type NewListingsStats } from '../api/client';

type ActiveTab = 'outperformers' | 'all_listings';

export default function NewListingsTracker() {
  // Navigation Menu Tab State
  const [activeTab, setActiveTab] = useState<ActiveTab>('outperformers');

  // Core Data State
  const [stats, setStats] = useState<NewListingsStats | null>(null);
  const [outperformers, setOutperformers] = useState<NewlyListedStock[]>([]);
  const [allStocks, setAllStocks] = useState<NewlyListedStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tab 2: All Stocks Filters & Pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [timeframeDays, setTimeframeDays] = useState<number>(365);
  const [sortBy, setSortBy] = useState<string>('listing_date');
  const [sortOrder, setSortOrder] = useState<string>('desc');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const pageSize = 20;

  // Tab 1: Outperformers Filters
  const [outperformerTier, setOutperformerTier] = useState<string>('ALL');

  // Filter out old re-listed symbols (True by default to show only genuine fresh IPOs)
  const [onlyFreshIpos, setOnlyFreshIpos] = useState<boolean>(true);


  // Load initial stats & outperformers
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, outRes] = await Promise.all([
        newListingsAPI.getStats(),
        newListingsAPI.getOutperformers({
          tier: outperformerTier,
          include_relisted: !onlyFreshIpos,
          limit: 100,
        }),
      ]);
      setStats(statsRes);
      setOutperformers(outRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load new listings tracker data');
    } finally {
      setLoading(false);
    }
  };

  // Load paginated list of all stocks
  const loadAllStocks = async () => {
    setTableLoading(true);
    try {
      const res = await newListingsAPI.getAll({
        search: searchQuery || undefined,
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
        timeframe_days: timeframeDays,
        only_fresh_ipos: onlyFreshIpos,
        sort_by: sortBy,
        order: sortOrder,
        page: currentPage,
        limit: pageSize,
      });
      setAllStocks(res.items);
      setTotalPages(res.pages);
      setTotalCount(res.total);
    } catch (err: any) {
      console.error('Error fetching all stocks:', err);
    } finally {
      setTableLoading(false);
    }
  };

  // Initial stats & outperformers on mount, tier change, or fresh IPO toggle
  useEffect(() => {
    loadData();
  }, [outperformerTier, onlyFreshIpos]);

  // Load all stocks on filter/page change or fresh IPO toggle
  useEffect(() => {
    loadAllStocks();
  }, [searchQuery, selectedCategory, timeframeDays, onlyFreshIpos, sortBy, sortOrder, currentPage]);


  // Manual refresh handler
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await newListingsAPI.refresh();
      await Promise.all([loadData(), loadAllStocks()]);
    } catch (err: any) {
      alert(`Refresh error: ${err.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  // Formatters
  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return '—';
    return `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatReturn = (val?: number) => {
    if (val === undefined || val === null) return '0.00%';
    const prefix = val > 0 ? '+' : '';
    return `${prefix}${val.toFixed(2)}%`;
  };

  const getTierBadge = (tier?: string) => {
    switch (tier) {
      case 'MULTIBAGGER':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 whitespace-nowrap">
            <span>🚀</span> Multibagger
          </span>
        );
      case 'HIGH_FLYER':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 whitespace-nowrap">
            <span>🔥</span> High Flyer
          </span>
        );
      case 'OUTPERFORMER':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-electric-500/20 text-electric-300 border border-electric-500/40 whitespace-nowrap">
            <span>⭐</span> Outperformer
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] text-gray-400 bg-navy-700/50 border border-navy-600 whitespace-nowrap">
            Neutral
          </span>
        );
    }
  };

  const getCategoryBadge = (category?: string) => {
    if (!category) return <span className="text-gray-500 text-[11px]">Small Cap</span>;
    if (category.toLowerCase().includes('large')) {
      return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 whitespace-nowrap">Large Cap</span>;
    }
    if (category.toLowerCase().includes('mid')) {
      return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap">Mid Cap</span>;
    }
    return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 whitespace-nowrap">Small Cap</span>;
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-2.5 pb-6">
      {/* ─── Top Compact Header Strip ─── */}
      <div className="flex items-center justify-between gap-2 border-b border-navy-700/60 pb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-1.5">
            <span>🚀</span> New Listings Tracker
          </h1>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-electric-500/20 text-electric-400 border border-electric-500/30">
            1-Year Surveillance
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Fresh IPOs Filter Toggle */}
          <div className="flex items-center gap-1.5 bg-navy-900/90 px-2.5 py-1 rounded-lg border border-navy-700 shadow-sm text-xs">
            <span className="text-[11px] font-medium text-gray-300 flex items-center gap-1">
              <span>✨</span> Fresh IPOs
            </span>
            <button
              type="button"
              onClick={() => setOnlyFreshIpos(!onlyFreshIpos)}
              className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none ${
                onlyFreshIpos ? 'bg-emerald-500' : 'bg-navy-700'
              }`}
              title="Filter out old companies that were merely cross-listed or migrated from BSE"
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  onlyFreshIpos ? 'translate-x-3.5' : 'translate-x-0.5'
                }`}
              />
            </button>
            <span className={`text-[10px] font-bold ${onlyFreshIpos ? 'text-emerald-400' : 'text-gray-400'}`}>
              {onlyFreshIpos ? 'Filtered' : 'All'}
            </span>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-navy-800 hover:bg-navy-700 text-gray-200 text-xs font-medium border border-navy-600 transition shadow-sm hover:border-electric-500/40 disabled:opacity-50"
          >
            <span className={`inline-block ${refreshing ? 'animate-spin' : ''}`}>🔄</span>
            <span>{refreshing ? 'Syncing...' : 'Sync'}</span>
          </button>
        </div>
      </div>

      {/* ─── Ultra-Compact KPI Metrics Strip ─── */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          <div className="glass-card px-3 py-1.5 border-l-2 border-l-electric-500 flex items-center justify-between">
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              {onlyFreshIpos ? 'Fresh IPOs (1Y)' : 'Total Listings'}
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm sm:text-base font-bold text-white">
                {onlyFreshIpos ? stats.fresh_ipos_count : stats.total_listings}
              </span>
              <span className="text-[10px] text-gray-500">
                {onlyFreshIpos ? `(${stats.relisted_count} old)` : '(NSE/BSE)'}
              </span>
            </div>
          </div>

          <div className="glass-card px-3 py-1.5 border-l-2 border-l-emerald-500 flex items-center justify-between">
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              Outperformers (&gt;20%)
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-sm sm:text-base font-bold text-emerald-400">
                {stats.outperformers_count}
              </span>
              <span className="text-[10px] font-semibold text-emerald-400/80">({stats.outperformers_pct}%)</span>
            </div>
          </div>

          <div className="glass-card px-3 py-1.5 border-l-2 border-l-purple-500 flex items-center justify-between">
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              #1 Top Gainer
            </span>
            <div className="flex items-baseline gap-1 truncate">
              <span className="text-xs sm:text-sm font-bold text-purple-300 truncate">
                {stats.top_performer?.symbol || '—'}
              </span>
              <span className="text-[10px] text-purple-400 font-semibold whitespace-nowrap">
                {stats.top_performer ? `+${stats.top_performer.return_pct.toLocaleString()}%` : ''}
              </span>
            </div>
          </div>

          <div className="glass-card px-3 py-1.5 border-l-2 border-l-amber-500 flex items-center justify-between">
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              Median / Avg Return
            </span>
            <div className="flex items-baseline gap-1">
              <span className={`text-xs sm:text-sm font-bold ${stats.median_return_pct >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {formatReturn(stats.median_return_pct)}
              </span>
              <span className="text-[10px] text-gray-500">
                ({formatReturn(stats.average_return_pct)})
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ─── Loading / Error Alerts ─── */}
      {loading && !refreshing && (
        <div className="p-2.5 rounded-xl bg-navy-800/80 border border-electric-500/30 text-electric-400 text-xs flex items-center gap-2">
          <div className="w-3.5 h-3.5 border-2 border-electric-400 border-t-transparent rounded-full animate-spin" />
          <span>Loading 1-year newly listed stocks and outperformer analytics...</span>
        </div>
      )}
      {error && (
        <div className="p-2.5 rounded-xl bg-coral-500/10 border border-coral-500/30 text-coral-400 text-xs flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={loadData} className="underline hover:text-white">Retry</button>
        </div>
      )}

      {/* ─── Compact Two-Menu Navigation Tabs ─── */}
      <div className="bg-navy-900/90 p-1 rounded-xl border border-navy-700/80 flex items-center justify-between gap-1 shadow-sm">
        <div className="grid grid-cols-2 w-full gap-1">
          {/* MENU 1: TOP OUTPERFORMERS */}
          <button
            onClick={() => setActiveTab('outperformers')}
            className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg font-semibold text-xs sm:text-sm transition-all duration-200 ${
              activeTab === 'outperformers'
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-sm ring-1 ring-emerald-400/40'
                : 'text-gray-400 hover:text-white hover:bg-navy-800/70'
            }`}
          >
            <span>🏆</span>
            <span className="truncate">Top Outperformers</span>
            {stats && (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  activeTab === 'outperformers' ? 'bg-black/25 text-emerald-100' : 'bg-navy-800 text-gray-400'
                }`}
              >
                {stats.outperformers_count}
              </span>
            )}
          </button>

          {/* MENU 2: ALL LISTED STOCKS (<1 YEAR) */}
          <button
            onClick={() => setActiveTab('all_listings')}
            className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg font-semibold text-xs sm:text-sm transition-all duration-200 ${
              activeTab === 'all_listings'
                ? 'bg-gradient-to-r from-electric-600 to-blue-600 text-white shadow-sm ring-1 ring-electric-400/40'
                : 'text-gray-400 hover:text-white hover:bg-navy-800/70'
            }`}
          >
            <span>📋</span>
            <span className="truncate">{onlyFreshIpos ? 'Fresh IPOs (<1Y)' : 'All Listed Stocks (<1Y)'}</span>
            {stats && (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  activeTab === 'all_listings' ? 'bg-black/25 text-blue-100' : 'bg-navy-800 text-gray-400'
                }`}
              >
                {onlyFreshIpos ? stats.fresh_ipos_count : stats.total_listings}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════════
          VIEW 1: TOP PERFORMING NEWLY LISTED STOCKS (OUTPERFORMERS)
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'outperformers' && (
        <div className="space-y-2 animate-fadeIn">
          {/* Top 3 Slim Champion Strip */}
          {outperformers.length >= 3 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {/* Rank 2 (Silver) */}
              <div className="glass-card px-3 py-1.5 border border-gray-400/30 bg-navy-800/80 flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-base">🥈</span>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-white truncate">
                      {outperformers[1].symbol}
                      <span className="ml-1.5 text-[10px] font-normal text-gray-400">{formatCurrency(outperformers[1].current_price)}</span>
                    </div>
                    <div className="text-[10px] text-gray-400 truncate">{outperformers[1].company_name}</div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs font-bold text-emerald-400">{formatReturn(outperformers[1].return_since_listing_pct)}</div>
                  <div className="text-[9px] text-gray-500">Return</div>
                </div>
              </div>

              {/* Rank 1 (Gold) */}
              <div className="glass-card px-3 py-1.5 border border-amber-400/60 bg-gradient-to-r from-amber-500/15 via-navy-800/90 to-navy-800 flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-lg">🥇</span>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-amber-300 truncate">
                      {outperformers[0].symbol}
                      <span className="ml-1.5 text-[10px] font-normal text-gray-300">{formatCurrency(outperformers[0].current_price)}</span>
                    </div>
                    <div className="text-[10px] text-gray-300 truncate">{outperformers[0].company_name}</div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-black text-amber-300">{formatReturn(outperformers[0].return_since_listing_pct)}</div>
                  <div className="text-[9px] text-amber-400/80">#1 Winner</div>
                </div>
              </div>

              {/* Rank 3 (Bronze) */}
              <div className="glass-card px-3 py-1.5 border border-amber-700/30 bg-navy-800/80 flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-base">🥉</span>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-white truncate">
                      {outperformers[2].symbol}
                      <span className="ml-1.5 text-[10px] font-normal text-gray-400">{formatCurrency(outperformers[2].current_price)}</span>
                    </div>
                    <div className="text-[10px] text-gray-400 truncate">{outperformers[2].company_name}</div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs font-bold text-emerald-400">{formatReturn(outperformers[2].return_since_listing_pct)}</div>
                  <div className="text-[9px] text-gray-500">Return</div>
                </div>
              </div>
            </div>
          )}

          {/* Outperformer Controls & Table Header Toolbar */}
          <div className="glass-card p-2.5 sm:p-3 border border-emerald-500/30 bg-gradient-to-br from-navy-900 via-navy-800/90 to-navy-900">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-navy-700/60">
              <div className="flex items-center gap-2">
                <span className="text-sm">🌟</span>
                <span className="text-xs sm:text-sm font-bold text-white">
                  Leaderboard
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  &gt;20% Gain
                </span>
              </div>

              {/* Tier Filter Pills */}
              <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                {[
                  { id: 'ALL', label: 'All Outperformers' },
                  { id: 'HIGH_FLYER', label: 'High Flyers (>50%)' },
                  { id: 'MULTIBAGGER', label: 'Multibaggers (>100%)' },
                ].map((tier) => (
                  <button
                    key={tier.id}
                    onClick={() => setOutperformerTier(tier.id)}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold whitespace-nowrap transition ${
                      outperformerTier === tier.id
                        ? 'bg-emerald-500 text-white shadow-sm'
                        : 'text-gray-400 hover:text-white bg-navy-900/80 border border-navy-700'
                    }`}
                  >
                    {tier.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Outperformers Table with Internal Scroll to Prevent Page Sprawl */}
            <div className="overflow-hidden rounded-xl border border-navy-700/80 bg-navy-900/60">
              <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-navy-900 text-[10px] uppercase text-gray-400 font-semibold tracking-wider z-10 border-b border-navy-700">
                    <tr>
                      <th className="py-2 px-2.5 whitespace-nowrap">Rank</th>
                      <th className="py-2 px-2.5 min-w-[150px]">Symbol & Company</th>
                      <th className="py-2 px-2.5 whitespace-nowrap">Tier</th>
                      <th className="py-2 px-2.5 whitespace-nowrap">Listing Date</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">Listing Price</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">CMP</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">Return Since Listing</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">All-Time High</th>
                      <th className="py-2 px-2.5 text-center whitespace-nowrap">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-700/50 text-gray-300">
                    {outperformers.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-gray-500">
                          No outperformers match the selected tier filter.
                        </td>
                      </tr>
                    ) : (
                      outperformers.map((stock, idx) => (
                        <tr key={stock.id} className="hover:bg-navy-800/50 transition">
                          <td className="py-1.5 px-2.5 font-mono font-semibold text-gray-400">
                            #{stock.performance_rank || idx + 1}
                          </td>
                          <td className="py-1.5 px-2.5">
                            <div className="font-bold text-white flex items-center gap-1.5 flex-wrap">
                              <span>{stock.symbol}</span>
                              {stock.is_relisted ? (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                  Re-listed
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                  Fresh IPO
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-gray-400 truncate max-w-[180px] sm:max-w-xs">
                              {stock.company_name}
                            </div>
                          </td>

                          <td className="py-1.5 px-2.5">{getCategoryBadge(stock.category)}</td>
                          <td className="py-1.5 px-2.5 whitespace-nowrap">
                            <div className="text-xs text-gray-200">{stock.listing_date}</div>
                            <div className="text-[9px] text-gray-500">{stock.days_since_listing}d ago</div>
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-mono text-gray-400 whitespace-nowrap">
                            {formatCurrency(stock.listing_price)}
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-mono font-semibold text-white whitespace-nowrap">
                            {formatCurrency(stock.current_price)}
                          </td>
                          <td className="py-1.5 px-2.5 text-right whitespace-nowrap">
                            <span className="font-mono font-bold text-emerald-400 text-xs sm:text-sm">
                              {formatReturn(stock.return_since_listing_pct)}
                            </span>
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-mono text-[10px] text-gray-400 whitespace-nowrap">
                            {formatCurrency(stock.all_time_high)}
                          </td>
                          <td className="py-1.5 px-2.5 text-center whitespace-nowrap">
                            {getTierBadge(stock.performance_tier)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          VIEW 2: ALL NEWLY LISTED STOCKS (PAST 1 YEAR)
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'all_listings' && (
        <div className="space-y-2 animate-fadeIn">
          <div className="glass-card p-2.5 sm:p-3 border border-navy-700/80">
            {/* Header & Timeframe Chips */}
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-navy-700/60">
              <div className="flex items-center gap-2">
                <span className="text-sm">📋</span>
                <span className="text-xs sm:text-sm font-bold text-white">
                  Directory
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-navy-700 text-gray-300 border border-navy-600">
                  {totalCount} Total
                </span>
              </div>

              {/* Timeframe Chips */}
              <div className="flex items-center gap-1 bg-navy-900 p-0.5 rounded-lg border border-navy-700 text-[11px] self-start sm:self-auto">
                {[
                  { days: 365, label: '1 Year' },
                  { days: 180, label: '6M' },
                  { days: 90, label: '90D' },
                  { days: 30, label: '30D' },
                ].map((tf) => (
                  <button
                    key={tf.days}
                    onClick={() => {
                      setTimeframeDays(tf.days);
                      setCurrentPage(1);
                    }}
                    className={`px-2 py-0.5 rounded-md font-medium whitespace-nowrap transition text-[11px] ${
                      timeframeDays === tf.days
                        ? 'bg-electric-500 text-white shadow-sm'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter Controls (Compact Responsive Single Row) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2.5">
              {/* Search Input */}
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search symbol / name..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-electric-500"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1 text-xs text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-electric-500"
              >
                <option value="All">All Categories</option>
                <option value="Large Cap">Large Cap</option>
                <option value="Mid Cap">Mid Cap</option>
                <option value="Small Cap">Small Cap</option>
              </select>

              {/* Sort By Field */}
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-electric-500"
              >
                <option value="listing_date">Sort: Listing Date</option>
                <option value="return_pct">Sort: Return %</option>
                <option value="mcap">Sort: Market Cap</option>
                <option value="price">Sort: Price</option>
                <option value="change">Sort: 1D Change</option>
              </select>

              {/* Sort Direction Button */}
              <button
                onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                className="w-full py-1 rounded-lg text-xs font-medium border border-navy-700 bg-navy-900 text-gray-300 hover:text-white hover:border-electric-500 flex items-center justify-center gap-1 transition"
              >
                <span>{sortOrder === 'desc' ? '⬇ High / Newest' : '⬆ Low / Oldest'}</span>
              </button>
            </div>

            {/* Table with Sticky Header and Internal Scroll */}
            <div className="overflow-hidden rounded-xl border border-navy-700/80 bg-navy-900/60">
              <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-navy-900 text-[10px] uppercase text-gray-400 font-semibold tracking-wider z-10 border-b border-navy-700">
                    <tr>
                      <th className="py-2 px-2.5 whitespace-nowrap">Symbol</th>
                      <th className="py-2 px-2.5 min-w-[150px]">Company Name</th>
                      <th className="py-2 px-2.5 whitespace-nowrap">Category</th>
                      <th className="py-2 px-2.5 whitespace-nowrap">Listing Date</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">Listing Price</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">CMP</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">Return Since Listing</th>
                      <th className="py-2 px-2.5 text-right whitespace-nowrap">All-Time High</th>
                      <th className="py-2 px-2.5 text-center whitespace-nowrap">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-700/50 text-gray-300">
                    {tableLoading ? (
                      <tr>
                        <td colSpan={9} className="py-12 text-center text-gray-400">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-4 h-4 border-2 border-electric-400 border-t-transparent rounded-full animate-spin" />
                            <span>Loading page results...</span>
                          </div>
                        </td>
                      </tr>
                    ) : allStocks.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-10 text-center text-gray-500">
                          No newly listed stocks match the selected filters.
                        </td>
                      </tr>
                    ) : (
                      allStocks.map((stock) => {
                        const ret = stock.return_since_listing_pct || 0;
                        const isPositive = ret > 0;
                        const isZero = ret === 0;

                        return (
                          <tr key={stock.id} className="hover:bg-navy-800/50 transition">
                            <td className="py-1.5 px-2.5 font-mono font-bold text-white whitespace-nowrap">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span>{stock.symbol}</span>
                                {stock.is_relisted ? (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                    Re-listed
                                  </span>
                                ) : (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                    IPO
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="py-1.5 px-2.5">
                              <div className="text-xs font-medium text-gray-200 truncate max-w-[180px] sm:max-w-xs">
                                {stock.company_name}
                              </div>
                            </td>
                            <td className="py-1.5 px-2.5 whitespace-nowrap">{getCategoryBadge(stock.category)}</td>
                            <td className="py-1.5 px-2.5 whitespace-nowrap">
                              <div className="text-xs text-gray-300 font-mono">{stock.listing_date}</div>
                              <div className="text-[9px] text-gray-500">{stock.days_since_listing}d ago</div>
                            </td>
                            <td className="py-1.5 px-2.5 text-right font-mono text-gray-400 whitespace-nowrap">
                              {formatCurrency(stock.listing_price)}
                            </td>
                            <td className="py-1.5 px-2.5 text-right font-mono font-semibold text-white whitespace-nowrap">
                              {formatCurrency(stock.current_price)}
                            </td>
                            <td className="py-1.5 px-2.5 text-right whitespace-nowrap">
                              <span
                                className={`font-mono font-bold text-xs sm:text-sm ${
                                  isPositive ? 'text-emerald-400' : isZero ? 'text-gray-400' : 'text-coral-400'
                                }`}
                              >
                                {formatReturn(ret)}
                              </span>
                            </td>
                            <td className="py-1.5 px-2.5 text-right font-mono text-[10px] text-gray-400 whitespace-nowrap">
                              {formatCurrency(stock.all_time_high)}
                            </td>
                            <td className="py-1.5 px-2.5 text-center whitespace-nowrap">
                              {stock.is_outperformer ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                  ⭐ Outperformer
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] text-gray-500 bg-navy-800 border border-navy-700">
                                  Listed
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-2 pt-2 border-t border-navy-700/60 text-xs text-gray-400">
                <div>
                  Page <span className="font-semibold text-white">{currentPage}</span> of{' '}
                  <span className="font-semibold text-white">{totalPages}</span> ({totalCount} stocks)
                </div>
                <div className="flex items-center gap-1.5 self-center sm:self-auto">
                  <button
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="px-2.5 py-1 rounded-lg bg-navy-800 border border-navy-700 hover:bg-navy-700 text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    Prev
                  </button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum = i + 1;
                      if (currentPage > 3 && totalPages > 5) {
                        pageNum = currentPage - 2 + i;
                        if (pageNum > totalPages) pageNum = totalPages - 4 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`w-7 h-7 rounded-lg font-mono text-xs font-medium transition ${
                            currentPage === pageNum
                              ? 'bg-electric-500 text-white'
                              : 'bg-navy-800 text-gray-400 hover:text-white border border-navy-700'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    className="px-2.5 py-1 rounded-lg bg-navy-800 border border-navy-700 hover:bg-navy-700 text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
