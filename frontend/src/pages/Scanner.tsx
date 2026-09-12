import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import ScoreMeter from '../components/charts/ScoreMeter';
import Sparkline from '../components/charts/Sparkline';
import { screenerAPI } from '../api/client';
import type { ScreeningCandidate, SparklineData } from '../api/client';
import { useNavigate } from 'react-router-dom';

const setupBadgeClass: Record<string, string> = {
  VCP: 'badge-vcp',
  ACCUMULATION: 'badge-accumulation',
  EMA_PULLBACK: 'badge-pullback',
};

const setupLabel: Record<string, string> = {
  VCP: 'VCP Breakout',
  ACCUMULATION: 'Accumulation Cluster',
  EMA_PULLBACK: '20 EMA Pullback',
};

const capBadgeConfig: Record<string, { label: string; class: string; glow: string }> = {
  SMALLCAP: {
    label: '🚀 Smallcap (Nifty Small 250)',
    class: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
    glow: 'border-amber-500/40 hover:shadow-[0_0_20px_rgba(245,158,11,0.2)]',
  },
  MIDCAP: {
    label: '📈 Midcap (Nifty Mid 150)',
    class: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
    glow: 'border-purple-500/40 hover:shadow-[0_0_20px_rgba(168,85,247,0.2)]',
  },
  LARGECAP: {
    label: '🏛️ Largecap (Nifty 100)',
    class: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30',
    glow: 'border-cyan-500/40 hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]',
  },
};

export default function Scanner() {
  const [candidates, setCandidates] = useState<ScreeningCandidate[]>([]);
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    minScore: 0,
    setupType: '',
    capCategory: 'MID_SMALL', // Default to Mid & Smallcap for maximum swing alpha
    sortBy: 'score',
  });
  const [scanning, setScanning] = useState(false);
  const navigate = useNavigate();

  const fetchCandidates = () => {
    setLoading(true);
    screenerAPI
      .getCandidates({
        min_score: filter.minScore,
        setup_type: filter.setupType || undefined,
        cap_category: filter.capCategory,
        sort_by: filter.sortBy,
      })
      .then((data) => {
        setCandidates(data);
        // Fetch sparklines for each candidate
        data.forEach((c) => {
          screenerAPI
            .getSparkline(c.symbol, 20)
            .then((spark) => {
              setSparklines((prev) => ({
                ...prev,
                [c.symbol]: spark.map((s: SparklineData) => s.close_price),
              }));
            })
            .catch(() => {});
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCandidates();
  }, [filter]);

  const handleRunScan = () => {
    setScanning(true);
    screenerAPI
      .runScan()
      .then(() => {
        fetchCandidates();
      })
      .catch(console.error)
      .finally(() => setScanning(false));
  };

  const handleSizePosition = (candidate: ScreeningCandidate) => {
    const params = new URLSearchParams({
      symbol: candidate.symbol,
      entry: String(candidate.entry_price || 0),
      stop: String(candidate.stop_loss || 0),
    });
    navigate(`/calculator?${params}`);
  };

  if (loading && candidates.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
      </div>
    );
  }

  const isMidSmallActive = filter.capCategory === 'MID_SMALL';

  return (
    <div className="animate-fade-in">
      <Header
        title="Indian Equity Swing Scanner"
        subtitle="Institutional accumulation & VCP breakout detection across NSE Smallcap & Midcap universe"
      />

      {/* Market Cap Segment Selection Tabs */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Market Cap Universe:
          </span>
          <span className="text-xs text-electric-400 font-mono">
            {isMidSmallActive ? '⚡ High-Beta Swing Focus (Nifty Midcap 150 + Smallcap 250)' : 'Market Cap Filter'}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          <button
            onClick={() => setFilter({ ...filter, capCategory: 'MID_SMALL' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capCategory === 'MID_SMALL'
                ? 'bg-gradient-to-r from-purple-900/60 to-amber-900/60 border-amber-400/60 text-white shadow-lg shadow-amber-500/10 ring-1 ring-amber-400/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-amber-300">🌟 Mid & Smallcap</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/30 text-amber-200 font-mono">HIGH ALPHA</span>
            </div>
            <span className="text-[11px] opacity-75">Explosive multi-week swings</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capCategory: 'SMALLCAP' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capCategory === 'SMALLCAP'
                ? 'bg-amber-950/50 border-amber-500 text-white shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-amber-400">🚀 Smallcap Only</span>
              <span className="text-[10px] text-gray-400 font-mono">&lt; ₹10k Cr</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty Smallcap 250 Leaders</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capCategory: 'MIDCAP' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capCategory === 'MIDCAP'
                ? 'bg-purple-950/50 border-purple-500 text-white shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-purple-400">📈 Midcap Only</span>
              <span className="text-[10px] text-gray-400 font-mono">₹10k - 1L Cr</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty Midcap 150 Outperformers</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capCategory: 'ALL' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capCategory === 'ALL'
                ? 'bg-electric-950/50 border-electric-500 text-white shadow-lg shadow-electric-500/10 ring-1 ring-electric-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-electric-300">🌐 All Caps</span>
              <span className="text-[10px] text-gray-400 font-mono">Entire Universe</span>
            </div>
            <span className="text-[11px] opacity-75">Large, Mid & Small blended</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capCategory: 'LARGECAP' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capCategory === 'LARGECAP'
                ? 'bg-cyan-950/50 border-cyan-500 text-white shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-cyan-400">🏛️ Largecap Only</span>
              <span className="text-[10px] text-gray-400 font-mono">&gt; ₹1L Cr</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty 50 & Bluechips</span>
          </button>
        </div>
      </div>

      {/* Info Callout for Mid & Smallcap Swing Trading */}
      {(filter.capCategory === 'MID_SMALL' || filter.capCategory === 'SMALLCAP' || filter.capCategory === 'MIDCAP') && (
        <div className="mb-6 p-4 rounded-xl bg-navy-900/80 border border-navy-700 flex items-start gap-3">
          <div className="text-xl">💡</div>
          <div className="text-xs leading-relaxed text-gray-300">
            <span className="font-semibold text-white">Smallcap & Midcap Swing Edge:</span> Stocks in these segments exhibit higher relative strength and volatility expansion following tight base consolidations. Dynamic institutional liquidity gates are active ({filter.capCategory === 'SMALLCAP' ? 'Turnover ≥ ₹5 Cr' : filter.capCategory === 'MIDCAP' ? 'Turnover ≥ ₹15 Cr' : 'Turnover ≥ ₹5 Cr (Smallcap) / ₹15 Cr (Midcap)'}) to capture high-velocity breakouts without getting trapped in illiquid circuits.
          </div>
        </div>
      )}

      {/* Filters Bar */}
      <div className="glass-card p-4 mb-6 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Min Score:</label>
          <select
            value={filter.minScore}
            onChange={(e) => setFilter({ ...filter, minScore: Number(e.target.value) })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value={0}>All Scores</option>
            <option value={60}>60+ (Solid)</option>
            <option value={70}>70+ (Strong)</option>
            <option value={80}>80+ (Exceptional)</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Setup:</label>
          <select
            value={filter.setupType}
            onChange={(e) => setFilter({ ...filter, setupType: e.target.value })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value="">All Setups</option>
            <option value="VCP">VCP Breakouts</option>
            <option value="ACCUMULATION">Accumulation Clusters</option>
            <option value="EMA_PULLBACK">20 EMA Pullbacks</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Sort By:</label>
          <select
            value={filter.sortBy}
            onChange={(e) => setFilter({ ...filter, sortBy: e.target.value })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value="score">Composite Score</option>
            <option value="turnover">Daily Turnover</option>
            <option value="delivery">Delivery %</option>
          </select>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-400 font-mono">
            <strong className="text-white">{candidates.length}</strong> swing candidates
          </span>
          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="btn-primary text-sm flex items-center gap-2"
          >
            {scanning ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Scanning NSE...
              </>
            ) : (
              '⚡ Scan Now'
            )}
          </button>
        </div>
      </div>

      {/* Candidate Cards Grid */}
      {candidates.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-gray-300 text-lg mb-2 font-semibold">No candidates match the selected filters</p>
          <p className="text-gray-500 text-sm">
            Try switching market cap segments above or lowering the minimum composite score.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {candidates.map((c, idx) => {
            const capConfig = capBadgeConfig[c.cap_category || 'MIDCAP'] || capBadgeConfig['MIDCAP'];
            return (
              <div
                key={c.id}
                className={`glass-card p-5 animate-slide-up transition-all duration-200 hover:-translate-y-1 ${capConfig.glow}`}
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                {/* Top Row: Symbol, Market Cap & Setup Badge */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <h3 className="text-lg font-bold text-white tracking-wide">{c.symbol}</h3>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${capConfig.class}`}>
                        {c.cap_category || 'MIDCAP'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span>{c.sector || 'Equities'}</span>
                      {c.market_cap_cr && (
                        <>
                          <span>•</span>
                          <span className="font-mono text-gray-300">
                            ₹{c.market_cap_cr >= 100000 ? `${(c.market_cap_cr / 100000).toFixed(1)}L Cr` : `${c.market_cap_cr.toLocaleString('en-IN')} Cr`}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <ScoreMeter score={c.composite_score} size={56} strokeWidth={4} />
                </div>

                {/* Setup Badge */}
                <div className="mb-3">
                  <span className={setupBadgeClass[c.setup_type] || 'badge'}>
                    {setupLabel[c.setup_type] || c.setup_type}
                  </span>
                </div>

                {/* Sparkline (20-day trend) */}
                <div className="mb-4 flex justify-center bg-navy-950/40 py-2 rounded-lg border border-navy-800">
                  <Sparkline
                    data={sparklines[c.symbol] || []}
                    width={220}
                    height={46}
                    showDots
                  />
                </div>

                {/* Metrics Bar */}
                <div className="grid grid-cols-3 gap-2.5 mb-4">
                  <div className="text-center p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <p className="text-[10px] text-gray-400 uppercase font-medium">Delivery</p>
                    <p className="text-sm font-semibold text-white font-mono">
                      {c.delivery_pct?.toFixed(1)}%
                    </p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <p className="text-[10px] text-gray-400 uppercase font-medium">Turnover</p>
                    <p className="text-sm font-semibold text-white font-mono">
                      ₹{c.turnover_cr?.toFixed(1)}Cr
                    </p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <p className="text-[10px] text-gray-400 uppercase font-medium">R:R Target</p>
                    <p className="text-sm font-semibold text-emerald-400 font-mono">
                      1:{c.risk_reward_ratio?.toFixed(1)}
                    </p>
                  </div>
                </div>

                {/* Technical Trade Levels */}
                <div className="flex items-center justify-between text-xs mb-3 px-1 py-1.5 bg-navy-900/40 rounded border border-navy-800/60">
                  <div>
                    <span className="text-gray-500">Entry: </span>
                    <span className="text-white font-mono font-semibold">₹{c.entry_price?.toFixed(0)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Stop: </span>
                    <span className="text-coral-400 font-mono font-semibold">₹{c.stop_loss?.toFixed(0)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Target: </span>
                    <span className="text-emerald-400 font-mono font-semibold">₹{c.target_price?.toFixed(0)}</span>
                  </div>
                </div>

                {/* Rationale */}
                <p className="text-[11px] text-gray-400 leading-relaxed mb-4 line-clamp-2">
                  {c.rationale}
                </p>

                {/* Action CTA */}
                <button
                  onClick={() => handleSizePosition(c)}
                  className="w-full btn-primary text-xs py-2 font-semibold flex items-center justify-center gap-2"
                >
                  📐 Calculate Position Size
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
