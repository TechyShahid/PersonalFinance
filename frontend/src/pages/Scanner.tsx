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
  VCP: 'VCP',
  ACCUMULATION: 'Accumulation',
  EMA_PULLBACK: '20 EMA Pullback',
};

export default function Scanner() {
  const [candidates, setCandidates] = useState<ScreeningCandidate[]>([]);
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ minScore: 0, setupType: '', sortBy: 'score' });
  const [scanning, setScanning] = useState(false);
  const navigate = useNavigate();

  const fetchCandidates = () => {
    setLoading(true);
    screenerAPI
      .getCandidates({
        min_score: filter.minScore,
        setup_type: filter.setupType || undefined,
        sort_by: filter.sortBy,
      })
      .then((data) => {
        setCandidates(data);
        // Fetch sparklines for each candidate
        data.forEach((c) => {
          screenerAPI.getSparkline(c.symbol, 20).then((spark) => {
            setSparklines((prev) => ({
              ...prev,
              [c.symbol]: spark.map((s: SparklineData) => s.close_price),
            }));
          }).catch(() => {});
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
      .then((data) => {
        setCandidates(data);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <Header title="Swing Scanner" subtitle="Institutional accumulation pattern detection" />

      {/* Filters Bar */}
      <div className="glass-card p-4 mb-6 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Min Score:</label>
          <select
            value={filter.minScore}
            onChange={(e) => setFilter({ ...filter, minScore: Number(e.target.value) })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value={0}>All</option>
            <option value={50}>50+</option>
            <option value={60}>60+</option>
            <option value={70}>70+</option>
            <option value={80}>80+</option>
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
            <option value="VCP">VCP</option>
            <option value="ACCUMULATION">Accumulation</option>
            <option value="EMA_PULLBACK">EMA Pullback</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Sort:</label>
          <select
            value={filter.sortBy}
            onChange={(e) => setFilter({ ...filter, sortBy: e.target.value })}
            className="bg-navy-900 border border-navy-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-electric-500"
          >
            <option value="score">Score</option>
            <option value="turnover">Turnover</option>
            <option value="delivery">Delivery %</option>
          </select>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-500 font-mono">{candidates.length} candidates</span>
          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="btn-primary text-sm"
          >
            {scanning ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Scanning...
              </span>
            ) : (
              '⚡ Run Scan'
            )}
          </button>
        </div>
      </div>

      {/* Candidate Cards Grid */}
      {candidates.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">No candidates found</p>
          <p className="text-gray-500 text-sm">Try adjusting filters or running a fresh scan</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {candidates.map((c, idx) => (
            <div
              key={c.id}
              className="glass-card-hover p-5 animate-slide-up"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white">{c.symbol}</h3>
                  <span className={setupBadgeClass[c.setup_type] || 'badge'}>
                    {setupLabel[c.setup_type] || c.setup_type}
                  </span>
                </div>
                <ScoreMeter score={c.composite_score} size={56} strokeWidth={4} />
              </div>

              {/* Sparkline */}
              <div className="mb-4 flex justify-center">
                <Sparkline
                  data={sparklines[c.symbol] || []}
                  width={200}
                  height={48}
                  showDots
                />
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="text-center p-2 rounded-lg bg-navy-900/50">
                  <p className="text-[10px] text-gray-500 uppercase">Delivery</p>
                  <p className="text-sm font-semibold text-white font-mono">
                    {c.delivery_pct?.toFixed(1)}%
                  </p>
                </div>
                <div className="text-center p-2 rounded-lg bg-navy-900/50">
                  <p className="text-[10px] text-gray-500 uppercase">Turnover</p>
                  <p className="text-sm font-semibold text-white font-mono">
                    ₹{c.turnover_cr?.toFixed(0)}Cr
                  </p>
                </div>
                <div className="text-center p-2 rounded-lg bg-navy-900/50">
                  <p className="text-[10px] text-gray-500 uppercase">R:R</p>
                  <p className="text-sm font-semibold text-emerald-400 font-mono">
                    1:{c.risk_reward_ratio?.toFixed(1)}
                  </p>
                </div>
              </div>

              {/* Entry / Stop / Target */}
              <div className="flex items-center justify-between text-xs mb-4 px-1">
                <div>
                  <span className="text-gray-500">Entry </span>
                  <span className="text-white font-mono">₹{c.entry_price?.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-gray-500">SL </span>
                  <span className="text-coral-400 font-mono">₹{c.stop_loss?.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Target </span>
                  <span className="text-emerald-400 font-mono">₹{c.target_price?.toFixed(0)}</span>
                </div>
              </div>

              {/* Rationale */}
              <p className="text-[11px] text-gray-400 leading-relaxed mb-4 line-clamp-2">
                {c.rationale}
              </p>

              {/* CTA */}
              <button
                onClick={() => handleSizePosition(c)}
                className="w-full btn-primary text-sm"
              >
                📐 Size Position
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
