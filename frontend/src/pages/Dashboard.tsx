import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import DonutChart from '../components/charts/DonutChart';
import PerformanceChart from '../components/charts/PerformanceChart';
import { dashboardAPI } from '../api/client';
import type { DashboardSummary, PerformanceResponse, FiiDiiEntry } from '../api/client';

const formatCurrency = (val: number) => {
  if (Math.abs(val) >= 10000000) return `₹${(val / 10000000).toFixed(2)}Cr`;
  if (Math.abs(val) >= 100000) return `₹${(val / 100000).toFixed(2)}L`;
  return `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
};

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [fiiDii, setFiiDii] = useState<FiiDiiEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      dashboardAPI.getSummary(),
      dashboardAPI.getPerformance(90),
      dashboardAPI.getFiiDii(10),
    ]).then(([s, p, f]) => {
      setSummary(s);
      setPerformance(p);
      setFiiDii(f);
    }).catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!summary) return null;

  const donutSegments = [
    { label: 'Core Deployed', value: summary.core_deployed, color: '#4f6cf7' },
    { label: 'Core Cash', value: summary.core_cash, color: '#3b54d4' },
    { label: 'Satellite Deployed', value: summary.satellite_deployed, color: '#10b981' },
    { label: 'Satellite Cash', value: summary.satellite_cash, color: '#34d399' },
  ];

  const latestFiiDii = fiiDii[0];

  return (
    <div className="animate-fade-in">
      <Header title="Dashboard" subtitle="Portfolio overview & market pulse" />

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="metric-card animate-slide-up">
          <span className="metric-label">Total Capital</span>
          <span className="metric-value">{formatCurrency(summary.total_capital)}</span>
        </div>
        <div className="metric-card animate-slide-up animate-delay-100">
          <span className="metric-label">Unrealized P&L</span>
          <span className={`metric-value ${summary.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
            {summary.total_unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(summary.total_unrealized_pnl)}
          </span>
        </div>
        <div className="metric-card animate-slide-up animate-delay-200">
          <span className="metric-label">Realized P&L</span>
          <span className={`metric-value ${summary.total_realized_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
            {summary.total_realized_pnl >= 0 ? '+' : ''}{formatCurrency(summary.total_realized_pnl)}
          </span>
        </div>
        <div className="metric-card animate-slide-up animate-delay-300">
          <span className="metric-label">Win Rate</span>
          <span className="metric-value text-gradient">{summary.win_rate}%</span>
          <span className="text-xs text-gray-500">{summary.total_trades} trades closed</span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Portfolio Composition */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Portfolio Composition</h3>
          <DonutChart
            segments={donutSegments}
            centerValue={formatCurrency(summary.total_capital)}
            centerLabel="Total Capital"
          />
        </div>

        {/* Performance Chart */}
        <div className="glass-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Performance vs Benchmarks</h3>
            <span className="text-xs text-gray-500 font-mono">Last 90 days</span>
          </div>
          {performance && (
            <PerformanceChart
              data={performance.data}
              portfolioReturn={performance.portfolio_return_pct}
              niftyReturn={performance.nifty_50_return_pct}
              midcapReturn={performance.nifty_midcap_return_pct}
            />
          )}
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Swing Trades */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Active Swing Trades</h3>
            <span className="badge-open">
              {summary.active_swing_trades} / {summary.max_concurrent_swings}
            </span>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Capacity Used</span>
              <span className="font-mono text-white">
                {Math.round((summary.active_swing_trades / summary.max_concurrent_swings) * 100)}%
              </span>
            </div>
            <div className="w-full h-2 bg-navy-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-electric-500 to-emerald-400 rounded-full transition-all duration-700"
                style={{
                  width: `${(summary.active_swing_trades / summary.max_concurrent_swings) * 100}%`,
                }}
              />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="p-3 rounded-lg bg-navy-900/50">
                <p className="text-xs text-gray-500 mb-1">Satellite Deployed</p>
                <p className="text-sm font-semibold text-white font-mono">
                  {formatCurrency(summary.satellite_deployed)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-navy-900/50">
                <p className="text-xs text-gray-500 mb-1">Satellite Cash</p>
                <p className="text-sm font-semibold text-emerald-400 font-mono">
                  {formatCurrency(summary.satellite_cash)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* FII/DII Sentiment */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">FII/DII Sentiment (Last 5 Days)</h3>
          <div className="space-y-3">
            {fiiDii.slice(0, 5).map((entry) => (
              <div key={entry.trade_date} className="flex items-center gap-3 text-xs">
                <span className="text-gray-500 font-mono w-20">
                  {new Date(entry.trade_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
                </span>
                <div className="flex-1 flex items-center gap-2">
                  <span className="text-gray-400 w-6">FII</span>
                  <div className="flex-1 h-4 bg-navy-900 rounded-full overflow-hidden relative">
                    <div
                      className={`h-full rounded-full ${entry.fii_net >= 0 ? 'bg-emerald-500/60' : 'bg-coral-500/60'}`}
                      style={{
                        width: `${Math.min(Math.abs(entry.fii_net) / 50, 100)}%`,
                        marginLeft: entry.fii_net < 0 ? 'auto' : undefined,
                      }}
                    />
                  </div>
                  <span className={`font-mono w-16 text-right ${entry.fii_net >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                    {entry.fii_net >= 0 ? '+' : ''}{(entry.fii_net / 100).toFixed(0)}
                  </span>
                </div>
                <div className="flex-1 flex items-center gap-2">
                  <span className="text-gray-400 w-6">DII</span>
                  <div className="flex-1 h-4 bg-navy-900 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${entry.dii_net >= 0 ? 'bg-emerald-500/60' : 'bg-coral-500/60'}`}
                      style={{
                        width: `${Math.min(Math.abs(entry.dii_net) / 50, 100)}%`,
                      }}
                    />
                  </div>
                  <span className={`font-mono w-16 text-right ${entry.dii_net >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                    {entry.dii_net >= 0 ? '+' : ''}{(entry.dii_net / 100).toFixed(0)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
