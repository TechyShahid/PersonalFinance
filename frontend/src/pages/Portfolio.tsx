import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import { portfolioAPI } from '../api/client';
import type { Holding, Portfolio as PortfolioType, TradeOrder } from '../api/client';

const formatCurrency = (val: number) =>
  `₹${Math.abs(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export default function Portfolio() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [portfolios, setPortfolios] = useState<PortfolioType[]>([]);
  const [activeOrders, setActiveOrders] = useState<TradeOrder[]>([]);
  const [activeTab, setActiveTab] = useState<'CORE' | 'SATELLITE'>('CORE');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      portfolioAPI.getPortfolios(),
      portfolioAPI.getHoldings(),
      portfolioAPI.getActiveOrders(),
    ]).then(([p, h, o]) => {
      setPortfolios(p);
      setHoldings(h);
      setActiveOrders(o);
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

  const corePortfolio = portfolios.find((p) => p.portfolio_type === 'CORE');
  const satellitePortfolio = portfolios.find((p) => p.portfolio_type === 'SATELLITE');
  const activePortfolio = activeTab === 'CORE' ? corePortfolio : satellitePortfolio;

  const filteredHoldings = holdings.filter((h) => {
    if (activeTab === 'CORE' && corePortfolio) return h.portfolio_id === corePortfolio.id;
    if (activeTab === 'SATELLITE' && satellitePortfolio) return h.portfolio_id === satellitePortfolio.id;
    return false;
  });

  const totalUnrealized = filteredHoldings.reduce((sum, h) => sum + (h.unrealized_pnl || 0), 0);

  return (
    <div className="animate-fade-in">
      <Header title="Portfolio" subtitle="Holdings & position management" />

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="metric-card">
          <span className="metric-label">Core Deployed</span>
          <span className="metric-value text-electric-400">{formatCurrency(corePortfolio?.deployed_capital || 0)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Core Cash</span>
          <span className="metric-value text-emerald-400">{formatCurrency(corePortfolio?.cash_available || 0)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Satellite Deployed</span>
          <span className="metric-value text-electric-400">{formatCurrency(satellitePortfolio?.deployed_capital || 0)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Satellite Cash</span>
          <span className="metric-value text-emerald-400">{formatCurrency(satellitePortfolio?.cash_available || 0)}</span>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="glass-card p-1.5 mb-6 inline-flex rounded-xl">
        {(['CORE', 'SATELLITE'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === tab
                ? 'bg-electric-500 text-white shadow-lg shadow-electric-500/25'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab === 'CORE' ? '💎 Long-Term Core (70%)' : '⚡ Satellite Swing (30%)'}
          </button>
        ))}
      </div>

      {/* Portfolio Stats Bar */}
      {activePortfolio && (
        <div className="glass-card p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-gray-400">Deployed: </span>
              <span className="font-mono text-white">{formatCurrency(activePortfolio.deployed_capital)}</span>
            </div>
            <div>
              <span className="text-gray-400">Cash: </span>
              <span className="font-mono text-emerald-400">{formatCurrency(activePortfolio.cash_available)}</span>
            </div>
            <div>
              <span className="text-gray-400">Unrealized P&L: </span>
              <span className={`font-mono font-semibold ${totalUnrealized >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                {totalUnrealized >= 0 ? '+' : '-'}{formatCurrency(totalUnrealized)}
              </span>
            </div>
          </div>
          <span className="text-xs text-gray-500">{filteredHoldings.length} positions</span>
        </div>
      )}

      {/* Holdings Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Price</th>
                <th>Current</th>
                <th>P&L</th>
                <th>P&L %</th>
                {activeTab === 'SATELLITE' && <th>Stop Loss</th>}
                {activeTab === 'SATELLITE' && <th>Target</th>}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredHoldings.length === 0 ? (
                <tr>
                  <td colSpan={activeTab === 'SATELLITE' ? 9 : 7} className="text-center py-8 text-gray-500">
                    No holdings in {activeTab.toLowerCase()} portfolio
                  </td>
                </tr>
              ) : (
                filteredHoldings.map((h) => {
                  const pnl = h.unrealized_pnl || 0;
                  const pnlPct = h.avg_buy_price > 0
                    ? ((h.current_price || 0) - h.avg_buy_price) / h.avg_buy_price * 100
                    : 0;
                  const isPositive = pnl >= 0;

                  return (
                    <tr key={h.id}>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{h.symbol}</span>
                          <span className="text-[10px] text-gray-500">{h.exchange}</span>
                        </div>
                      </td>
                      <td className="font-mono">{h.quantity}</td>
                      <td className="font-mono">₹{h.avg_buy_price.toFixed(2)}</td>
                      <td className="font-mono">₹{(h.current_price || 0).toFixed(2)}</td>
                      <td className={`font-mono font-semibold ${isPositive ? 'text-emerald-400' : 'text-coral-400'}`}>
                        {isPositive ? '+' : ''}{formatCurrency(pnl)}
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                          isPositive ? 'bg-emerald-500/15 text-emerald-400' : 'bg-coral-500/15 text-coral-400'
                        }`}>
                          {isPositive ? '+' : ''}{pnlPct.toFixed(1)}%
                        </span>
                      </td>
                      {activeTab === 'SATELLITE' && (
                        <td className="font-mono text-coral-400">
                          {h.stop_loss_price ? `₹${h.stop_loss_price.toFixed(0)}` : '—'}
                        </td>
                      )}
                      {activeTab === 'SATELLITE' && (
                        <td className="font-mono text-emerald-400">
                          {h.target_price ? `₹${h.target_price.toFixed(0)}` : '—'}
                        </td>
                      )}
                      <td>
                        <span className={h.status === 'ACTIVE' ? 'badge-open' : 'badge text-gray-500'}>
                          {h.status}
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

      {/* Active Orders */}
      {activeOrders.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Open Orders</h3>
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Stop</th>
                    <th>Target</th>
                    <th>Entry Date</th>
                  </tr>
                </thead>
                <tbody>
                  {activeOrders.map((o) => (
                    <tr key={o.id}>
                      <td className="font-semibold text-white">{o.symbol}</td>
                      <td><span className="badge-open">{o.order_type}</span></td>
                      <td className="font-mono">{o.quantity}</td>
                      <td className="font-mono">₹{o.entry_price.toFixed(2)}</td>
                      <td className="font-mono text-coral-400">
                        {o.stop_loss ? `₹${o.stop_loss.toFixed(0)}` : '—'}
                      </td>
                      <td className="font-mono text-emerald-400">
                        {o.target_price ? `₹${o.target_price.toFixed(0)}` : '—'}
                      </td>
                      <td className="text-gray-400 text-xs">
                        {new Date(o.entry_date).toLocaleDateString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
