import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import ScoreMeter from '../components/charts/ScoreMeter';
import Sparkline from '../components/charts/Sparkline';
import { midSmallScannerAPI, screenerAPI } from '../api/client';
import type { MidSmallSwingCandidate, SparklineData } from '../api/client';
import { useNavigate } from 'react-router-dom';

const setupBadgeClass: Record<string, string> = {
  VCP: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  PULLBACK: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  BREAKOUT: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
  ACCUMULATION: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30',
};

const setupLabel: Record<string, string> = {
  VCP: 'VCP Breakout (3-4 Contractions)',
  PULLBACK: '20 EMA Pullback (±0.8% Test)',
  BREAKOUT: 'Resistance Breakout (≥2x Vol)',
  ACCUMULATION: 'Institutional Accumulation',
};

const capBadgeConfig: Record<string, { label: string; class: string; glow: string }> = {
  SMALLCAP: {
    label: '🚀 Nifty Smallcap 250',
    class: 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
    glow: 'border-amber-500/30 hover:border-amber-400 hover:shadow-[0_0_25px_rgba(245,158,11,0.2)]',
  },
  MIDCAP: {
    label: '📈 Nifty Midcap 150',
    class: 'bg-purple-500/20 text-purple-300 border border-purple-500/40',
    glow: 'border-purple-500/30 hover:border-purple-400 hover:shadow-[0_0_25px_rgba(168,85,247,0.2)]',
  },
};

export default function Scanner() {
  const [candidates, setCandidates] = useState<MidSmallSwingCandidate[]>([]);
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    capType: 'all', // all | midcap | smallcap
    setup: 'all',   // all | vcp | pullback | breakout
    minTurnoverCr: 10,
    sortBy: 'score', // score | rs | delivery | turnover
  });
  const [scanning, setScanning] = useState(false);
  const navigate = useNavigate();

  const fetchCandidates = () => {
    setLoading(true);
    midSmallScannerAPI
      .getSwingCandidates({
        cap_type: filter.capType,
        setup: filter.setup,
        min_turnover_cr: filter.minTurnoverCr,
      })
      .then((data) => {
        // Client-side sorting
        let sorted = [...data];
        if (filter.sortBy === 'rs') {
          sorted.sort((a, b) => b.relative_strength_score - a.relative_strength_score);
        } else if (filter.sortBy === 'delivery') {
          sorted.sort((a, b) => b.delivery_multiple - a.delivery_multiple);
        } else if (filter.sortBy === 'turnover') {
          sorted.sort((a, b) => b.turnover_cr - a.turnover_cr);
        } else {
          sorted.sort((a, b) => b.composite_score - a.composite_score);
        }
        setCandidates(sorted);

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

  const handleSizePosition = (candidate: MidSmallSwingCandidate) => {
    const params = new URLSearchParams({
      symbol: candidate.symbol,
      entry: String(candidate.entry_price || 0),
      stop: String(candidate.suggested_stop_loss || 0),
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

  return (
    <div className="animate-fade-in">
      <Header
        title="Smallcap & Midcap Swing Scanner"
        subtitle="Institutional multi-factor scanner for Nifty Midcap 150 & Smallcap 250 momentum leaders"
      />

      {/* Market Cap Universe Segment Tabs */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Institutional Market Cap Universe:
          </span>
          <span className="text-xs text-electric-400 font-mono">
            Series EQ Only • ASM/GSM Stage 2+ Excluded • ADV ≥ 200k
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => setFilter({ ...filter, capType: 'all' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capType === 'all'
                ? 'bg-gradient-to-r from-purple-900/50 via-navy-900 to-amber-900/50 border-amber-400/60 text-white shadow-lg shadow-amber-500/10 ring-1 ring-amber-400/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-amber-300 text-sm">🌟 Mid & Smallcap (All)</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">HIGH ALPHA</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty Midcap 150 + Nifty Smallcap 250 universe</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capType: 'smallcap' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capType === 'smallcap'
                ? 'bg-amber-950/50 border-amber-500 text-white shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-amber-400 text-sm">🚀 Smallcap Only</span>
              <span className="text-[10px] text-gray-400 font-mono">Turnover ≥ ₹10 Cr</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty Smallcap 250 emerging breakout plays</span>
          </button>

          <button
            onClick={() => setFilter({ ...filter, capType: 'midcap' })}
            className={`px-4 py-3 rounded-xl text-xs font-semibold text-left transition-all duration-200 border flex flex-col justify-between ${
              filter.capType === 'midcap'
                ? 'bg-purple-950/50 border-purple-500 text-white shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/40'
                : 'bg-navy-900/60 border-navy-700/60 text-gray-400 hover:text-white hover:border-navy-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-purple-400 text-sm">📈 Midcap Only</span>
              <span className="text-[10px] text-gray-400 font-mono">Turnover ≥ ₹25 Cr</span>
            </div>
            <span className="text-[11px] opacity-75">Nifty Midcap 150 institutional leaders</span>
          </button>
        </div>
      </div>

      {/* Quantitative Guardrails Banner */}
      <div className="mb-6 p-4 rounded-xl bg-navy-900/90 border border-navy-700 flex items-start gap-3.5">
        <div className="text-2xl mt-0.5">🛡️</div>
        <div className="text-xs leading-relaxed text-gray-300">
          <div className="font-semibold text-white mb-1 flex items-center gap-2">
            Institutional Small/Midcap Swing Rules Active
            <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-300 font-mono">7:00 PM IST POST-BHAVCOPY</span>
          </div>
          <div className="text-gray-400 space-y-0.5">
            <p>• <strong>Liquidity & Impact Cost:</strong> ADV ≥ 200k shares | Turnover ≥ ₹10 Cr (Smallcaps) / ₹25 Cr (Midcaps)</p>
            <p>• <strong>Factor A & B:</strong> Delivery surge ≥ 1.8x 20-day SMA | Delivery % ≥ 45-60% | Close in top 25% of day range | Close &gt; 20 EMA &gt; 50 SMA</p>
            <p>• <strong>Mansfield RS:</strong> 21-day rolling outperformance ratio vs respective Nifty Midcap 150 / Smallcap 250 benchmark</p>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="glass-card p-4 mb-6 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Pattern Setup:</label>
          <select
            value={filter.setup}
            onChange={(e) => setFilter({ ...filter, setup: e.target.value })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value="all">All Setups</option>
            <option value="vcp">VCP (Volatility Contraction)</option>
            <option value="pullback">20-EMA Mean Reversion (±0.8% Band)</option>
            <option value="breakout">Resistance Breakout (≥2x Vol)</option>
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
            <option value="rs">Mansfield Relative Strength</option>
            <option value="delivery">Delivery Multiple (Surge)</option>
            <option value="turnover">Daily Turnover (₹ Cr)</option>
          </select>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-400 font-mono">
            <strong className="text-white">{candidates.length}</strong> qualified setups
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
              '⚡ Scan Engine'
            )}
          </button>
        </div>
      </div>

      {/* Candidate Cards Grid */}
      {candidates.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-gray-300 text-lg mb-2 font-semibold">No candidates match the selected filters</p>
          <p className="text-gray-500 text-sm">
            Try choosing 'All Setups' or switching between Midcap and Smallcap universes.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {candidates.map((c, idx) => {
            const capConfig = capBadgeConfig[c.market_cap_tier] || capBadgeConfig['MIDCAP'];
            const isRsPositive = c.relative_strength_score > 0;
            return (
              <div
                key={c.symbol}
                className={`glass-card p-5 animate-slide-up transition-all duration-200 hover:-translate-y-1 ${capConfig.glow}`}
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                {/* Top Row: Symbol, Company Name & Score */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold text-white tracking-wide">{c.symbol}</h3>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${capConfig.class}`}>
                        {c.market_cap_tier}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 truncate max-w-[210px]">{c.company_name}</p>
                    <div className="flex items-center gap-2 text-[11px] text-gray-500 mt-0.5">
                      <span>{c.sector}</span>
                      <span>•</span>
                      <span className="font-mono text-gray-400">₹{c.market_cap_cr?.toLocaleString('en-IN')} Cr</span>
                    </div>
                  </div>
                  <ScoreMeter score={c.composite_score} size={56} strokeWidth={4} />
                </div>

                {/* Setup Type Badge */}
                <div className="mb-3">
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md inline-block ${setupBadgeClass[c.setup_type] || 'badge'}`}>
                    {setupLabel[c.setup_type] || c.setup_type}
                  </span>
                </div>

                {/* Sparkline (20-day trend) */}
                <div className="mb-4 flex justify-center bg-navy-950/50 py-2 rounded-lg border border-navy-800">
                  <Sparkline
                    data={sparklines[c.symbol] || []}
                    width={220}
                    height={46}
                    showDots
                  />
                </div>

                {/* Institutional Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {/* Mansfield RS */}
                  <div className="p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <div className="flex items-center justify-between text-[10px] text-gray-400 uppercase font-medium">
                      <span>Mansfield RS</span>
                      <span className="text-[9px] text-gray-500 font-mono">21D</span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className={`text-sm font-bold font-mono ${isRsPositive ? 'text-emerald-400' : 'text-coral-400'}`}>
                        {isRsPositive ? '+' : ''}{c.relative_strength_score.toFixed(1)}
                      </span>
                      <span className="text-[10px] text-gray-500 truncate max-w-[85px] font-mono">
                        vs {c.rs_benchmark === 'NIFTYSMALLCAP250' ? 'Small 250' : 'Mid 150'}
                      </span>
                    </div>
                  </div>

                  {/* Delivery Multiple & Concentration */}
                  <div className="p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <div className="flex items-center justify-between text-[10px] text-gray-400 uppercase font-medium">
                      <span>Delivery Surge</span>
                      <span className="text-[9px] text-gray-500 font-mono">{c.delivery_pct}%</span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-sm font-bold font-mono text-purple-300">
                        {c.delivery_multiple.toFixed(1)}x SMA
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono">
                        ₹{c.deliverable_value_cr.toFixed(0)}Cr
                      </span>
                    </div>
                  </div>

                  {/* 20-Day ADV */}
                  <div className="p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <p className="text-[10px] text-gray-400 uppercase font-medium">20D ADV</p>
                    <p className="text-xs font-semibold text-white font-mono mt-1">
                      {c.adv_20d >= 1000000 ? `${(c.adv_20d / 1000000).toFixed(1)}M` : `${(c.adv_20d / 1000).toFixed(0)}k`} sh
                    </p>
                  </div>

                  {/* Daily Turnover */}
                  <div className="p-2 rounded-lg bg-navy-900/60 border border-navy-800">
                    <p className="text-[10px] text-gray-400 uppercase font-medium">Turnover</p>
                    <p className="text-xs font-semibold text-white font-mono mt-1">
                      ₹{c.turnover_cr.toFixed(1)} Cr
                    </p>
                  </div>
                </div>

                {/* Trade Execution Levels */}
                <div className="p-2.5 rounded-lg bg-navy-900/40 border border-navy-800/80 mb-3 text-xs">
                  <div className="flex items-center justify-between mb-1.5 pb-1.5 border-b border-navy-800">
                    <span className="text-gray-400">Entry / CMP:</span>
                    <span className="font-mono font-bold text-white">₹{c.entry_price.toFixed(2)}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div>
                      <p className="text-gray-500">Pivot</p>
                      <p className="font-mono font-semibold text-electric-300">₹{c.pivot_price.toFixed(0)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Stop Loss</p>
                      <p className="font-mono font-semibold text-coral-400">₹{c.suggested_stop_loss.toFixed(0)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Target (2.2R)</p>
                      <p className="font-mono font-semibold text-emerald-400">₹{c.target_price.toFixed(0)}</p>
                    </div>
                  </div>
                </div>

                {/* Institutional Rationale */}
                <p className="text-[11px] text-gray-400 leading-relaxed mb-4 line-clamp-2">
                  {c.rationale}
                </p>

                {/* Calculate Position Size Action */}
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
