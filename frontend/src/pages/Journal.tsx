import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import { journalAPI } from '../api/client';
import type { TradeOrder, JournalStats } from '../api/client';

const formatCurrency = (val: number) =>
  `₹${Math.abs(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export default function Journal() {
  const [trades, setTrades] = useState<TradeOrder[]>([]);
  const [stats, setStats] = useState<JournalStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      journalAPI.getTrades(),
      journalAPI.getStats(),
    ]).then(([t, s]) => {
      setTrades(t);
      setStats(s);
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

  return (
    <div className="animate-fade-in">
      <Header title="Trade Journal" subtitle="Historical trades, performance metrics & tax summary" />

      {stats && (
        <>
          {/* Performance Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="metric-card animate-slide-up">
              <span className="metric-label">Win Rate</span>
              <span className={`metric-value ${stats.win_rate >= 50 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {stats.win_rate}%
              </span>
              <span className="text-xs text-gray-500">
                {stats.winning_trades}W / {stats.losing_trades}L
              </span>
            </div>
            <div className="metric-card animate-slide-up animate-delay-100">
              <span className="metric-label">Avg R-Multiple</span>
              <span className={`metric-value ${stats.avg_r_multiple >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {stats.avg_r_multiple >= 0 ? '+' : ''}{stats.avg_r_multiple}R
              </span>
              <span className="text-xs text-gray-500">
                Avg hold: {stats.avg_hold_days} days
              </span>
            </div>
            <div className="metric-card animate-slide-up animate-delay-200">
              <span className="metric-label">Expectancy</span>
              <span className={`metric-value ${stats.expectancy >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {stats.expectancy >= 0 ? '+' : ''}{formatCurrency(stats.expectancy)}
              </span>
              <span className="text-xs text-gray-500">per trade expected</span>
            </div>
            <div className="metric-card animate-slide-up animate-delay-300">
              <span className="metric-label">Net P&L</span>
              <span className={`metric-value ${stats.total_net_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {stats.total_net_pnl >= 0 ? '+' : ''}{formatCurrency(stats.total_net_pnl)}
              </span>
              <span className="text-xs text-gray-500">after all costs & taxes</span>
            </div>
          </div>

          {/* Win/Loss & Tax Summary */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Win/Loss Breakdown */}
            <div className="glass-card p-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Win/Loss Analysis</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Average Win</span>
                  <span className="font-mono text-emerald-400 font-semibold">+{formatCurrency(stats.avg_win_amount)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Average Loss</span>
                  <span className="font-mono text-coral-400 font-semibold">{formatCurrency(stats.avg_loss_amount)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Max Drawdown</span>
                  <span className="font-mono text-coral-400 font-semibold">{formatCurrency(stats.max_drawdown)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Tax Paid</span>
                  <span className="font-mono text-amber-400 font-semibold">{formatCurrency(stats.total_tax_paid)}</span>
                </div>

                {/* Win rate bar */}
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Loss ({stats.losing_trades})</span>
                    <span>Win ({stats.winning_trades})</span>
                  </div>
                  <div className="h-3 bg-navy-900 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-coral-500/60 transition-all duration-700"
                      style={{ width: `${100 - stats.win_rate}%` }}
                    />
                    <div
                      className="h-full bg-emerald-500/60 transition-all duration-700"
                      style={{ width: `${stats.win_rate}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Tax Summary */}
            <div className="glass-card p-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Tax Summary (FY 2025-26)</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-gray-400">STCG (20%)</span>
                    <p className="text-[10px] text-gray-600">Short-term (&lt; 12 months)</p>
                  </div>
                  <span className="font-mono text-amber-400 font-semibold">{formatCurrency(stats.stcg_total)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-gray-400">LTCG (12.5%)</span>
                    <p className="text-[10px] text-gray-600">Above ₹1.25L exemption</p>
                  </div>
                  <span className="font-mono text-amber-400 font-semibold">{formatCurrency(stats.ltcg_total)}</span>
                </div>

                {/* Exemption tracker */}
                <div className="p-3 rounded-lg bg-navy-900/50">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="text-gray-400">LTCG Exemption (₹1.25L)</span>
                    <span className="font-mono text-gray-300">
                      ₹{(stats.ltcg_exemption_used / 1000).toFixed(1)}K used
                    </span>
                  </div>
                  <div className="h-2 bg-navy-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all duration-700"
                      style={{ width: `${Math.min((stats.ltcg_exemption_used / 125000) * 100, 100)}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-500 mt-1 text-right">
                    ₹{(stats.ltcg_exemption_remaining / 1000).toFixed(1)}K remaining
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Trade History Table */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-navy-700/50">
          <h3 className="text-sm font-semibold text-gray-300">Closed Trades</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>Qty</th>
                <th>Gross P&L</th>
                <th>Costs</th>
                <th>Tax</th>
                <th>Net P&L</th>
                <th>Hold</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-gray-500">
                    No closed trades yet
                  </td>
                </tr>
              ) : (
                trades.map((t) => {
                  const isWin = (t.realized_pnl || 0) > 0;
                  const holdDays = t.entry_date && t.exit_date
                    ? Math.ceil((new Date(t.exit_date).getTime() - new Date(t.entry_date).getTime()) / 86400000)
                    : 0;
                  const totalCosts = (t.stt_paid || 0) + (t.gst_paid || 0) + (t.sebi_fee || 0) + (t.brokerage || 0) + (t.stamp_duty || 0) + (t.exchange_txn_charge || 0);

                  return (
                    <tr key={t.id}>
                      <td className="font-semibold text-white">{t.symbol}</td>
                      <td className="font-mono text-xs">
                        ₹{t.entry_price.toFixed(0)}
                        <br />
                        <span className="text-gray-500">
                          {new Date(t.entry_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
                        </span>
                      </td>
                      <td className="font-mono text-xs">
                        ₹{(t.exit_price || 0).toFixed(0)}
                        <br />
                        <span className="text-gray-500">
                          {t.exit_date ? new Date(t.exit_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : '—'}
                        </span>
                      </td>
                      <td className="font-mono">{t.quantity}</td>
                      <td className={`font-mono font-semibold ${isWin ? 'text-emerald-400' : 'text-coral-400'}`}>
                        {isWin ? '+' : ''}{formatCurrency(t.realized_pnl || 0)}
                      </td>
                      <td className="font-mono text-gray-400 text-xs">₹{totalCosts.toFixed(0)}</td>
                      <td>
                        <div className="font-mono text-xs">
                          <span className="text-amber-400">₹{(t.tax_liability || 0).toFixed(0)}</span>
                          <br />
                          <span className="text-gray-500">{t.tax_type || '—'}</span>
                        </div>
                      </td>
                      <td className={`font-mono font-bold ${(t.net_return || 0) >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                        {(t.net_return || 0) >= 0 ? '+' : ''}{formatCurrency(t.net_return || 0)}
                      </td>
                      <td className="font-mono text-gray-400">{holdDays}d</td>
                      <td>
                        <span className={isWin ? 'badge-win' : 'badge-loss'}>
                          {t.status === 'TARGET_REACHED' || t.status === 'TAX_RECORDED' && isWin ? '🎯 Target' : '🛑 Stop'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
