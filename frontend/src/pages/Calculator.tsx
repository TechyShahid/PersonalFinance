import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from '../components/layout/Header';
import { calculatorAPI, symbolsAPI } from '../api/client';
import type { PositionSizeResponse } from '../api/client';

const formatCurrency = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export default function Calculator() {
  const [searchParams] = useSearchParams();

  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '');
  const [entry, setEntry] = useState(searchParams.get('entry') || '');
  const [stop, setStop] = useState(searchParams.get('stop') || '');
  const [capital, setCapital] = useState('750000');
  const [riskPct, setRiskPct] = useState('1.0');
  const [result, setResult] = useState<PositionSizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    symbolsAPI.getAll().then((data) => setSymbols(data.symbols)).catch(() => {});
  }, []);

  // Auto-calculate when params from scanner
  useEffect(() => {
    if (searchParams.get('symbol') && searchParams.get('entry') && searchParams.get('stop')) {
      handleCalculate();
    }
  }, []);

  const handleCalculate = useCallback(() => {
    const entryPrice = parseFloat(entry);
    const stopPrice = parseFloat(stop);
    const portfolioCapital = parseFloat(capital);
    const risk = parseFloat(riskPct);

    if (!symbol || isNaN(entryPrice) || isNaN(stopPrice) || entryPrice <= 0 || stopPrice <= 0) {
      setError('Please enter valid symbol, entry price, and stop loss');
      return;
    }

    if (stopPrice >= entryPrice) {
      setError('Stop loss must be below entry price for a long trade');
      return;
    }

    setError('');
    setLoading(true);
    calculatorAPI
      .positionSize({
        symbol: symbol.toUpperCase(),
        entry_price: entryPrice,
        stop_loss_price: stopPrice,
        portfolio_capital: isNaN(portfolioCapital) ? undefined : portfolioCapital,
        risk_pct: isNaN(risk) ? undefined : risk,
      })
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [symbol, entry, stop, capital, riskPct]);

  const filteredSymbols = symbols.filter((s) =>
    s.toLowerCase().startsWith(symbol.toLowerCase())
  ).slice(0, 8);

  const riskDistance = parseFloat(entry) && parseFloat(stop)
    ? (((parseFloat(entry) - parseFloat(stop)) / parseFloat(entry)) * 100)
    : 0;

  const isPennyTrade = searchParams.get('penny') === 'true' || (parseFloat(entry) > 0 && parseFloat(entry) <= 50);

  return (
    <div className="animate-fade-in">
      <Header title="Position Sizing Calculator" subtitle="ATR-based risk management & order sizing" />

      {isPennyTrade && (
        <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-yellow-950/40 via-navy-900 to-amber-950/30 border border-yellow-500/40 flex items-start gap-3.5 shadow-lg shadow-yellow-900/10">
          <div className="text-2xl mt-0.5">⚠️</div>
          <div className="text-xs leading-relaxed text-gray-300 w-full">
            <div className="font-semibold text-yellow-300 mb-1 flex items-center justify-between">
              <span>Penny Stock Position Guardrails Active (Price ≤ ₹50)</span>
              <span className="px-2 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-300 font-mono border border-yellow-500/30">
                CAP: 2.5% EQUITY
              </span>
            </div>
            <p className="text-gray-400">
              Penny stocks carry extreme circuit-lock and gap-down hazards. Enforce a maximum position size of <strong>2.0% - 2.5% of total portfolio equity</strong> (e.g. ₹62,500 max on a ₹25L book) and ensure total shares do not exceed <strong>5% of 20-day ADV</strong> for safe multi-day liquidation.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-5">Trade Parameters</h3>

          <div className="space-y-4">
            {/* Symbol */}
            <div className="relative">
              <label className="text-xs text-gray-400 mb-1 block">Stock Symbol (NSE)</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => {
                  setSymbol(e.target.value.toUpperCase());
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                placeholder="e.g. TATAMOTORS"
                className="input-field"
              />
              {showSuggestions && filteredSymbols.length > 0 && symbol.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-navy-800 border border-navy-600 rounded-xl shadow-lg z-10 max-h-48 overflow-y-auto">
                  {filteredSymbols.map((s) => (
                    <button
                      key={s}
                      onMouseDown={() => {
                        setSymbol(s);
                        setShowSuggestions(false);
                      }}
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-300 hover:bg-navy-700 hover:text-white transition-colors font-mono"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Entry Price */}
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Entry Price (₹)</label>
              <input
                type="number"
                value={entry}
                onChange={(e) => setEntry(e.target.value)}
                placeholder="0.00"
                step="0.05"
                className="input-field"
              />
            </div>

            {/* Stop Loss */}
            <div>
              <label className="text-xs text-gray-400 mb-1 flex items-center justify-between">
                <span>Stop Loss Price (₹)</span>
                {riskDistance > 0 && (
                  <span className={`font-mono ${riskDistance <= 6 ? 'text-emerald-400' : 'text-coral-400'}`}>
                    {riskDistance.toFixed(1)}% risk distance
                  </span>
                )}
              </label>
              <input
                type="number"
                value={stop}
                onChange={(e) => setStop(e.target.value)}
                placeholder="0.00"
                step="0.05"
                className="input-field"
              />
            </div>

            {/* Capital Override */}
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Satellite Capital (₹)</label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                placeholder="750000"
                className="input-field"
              />
            </div>

            {/* Risk % */}
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Max Risk per Trade (%)</label>
              <input
                type="number"
                value={riskPct}
                onChange={(e) => setRiskPct(e.target.value)}
                placeholder="1.0"
                step="0.1"
                min="0.1"
                max="5"
                className="input-field"
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-coral-500/10 border border-coral-500/30 text-coral-400 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full btn-primary text-sm py-3"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Calculating...
                </span>
              ) : (
                '🧮 Calculate Position Size'
              )}
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Primary Result */}
              <div className="glass-card p-6 border-glow">
                <div className="text-center mb-6">
                  <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Buy</p>
                  <p className="text-4xl font-bold text-gradient mb-1">{result.shares_to_buy} shares</p>
                  <p className="text-lg font-mono text-gray-300">{result.symbol} @ ₹{result.entry_price}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-navy-900/50 text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Total Investment</p>
                    <p className="text-sm font-bold text-white font-mono">
                      {formatCurrency(result.total_investment)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-navy-900/50 text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Risk Amount</p>
                    <p className="text-sm font-bold text-coral-400 font-mono">
                      {formatCurrency(result.risk_amount)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-navy-900/50 text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Risk % of Portfolio</p>
                    <p className="text-sm font-bold text-white font-mono">
                      {result.risk_pct_of_portfolio}%
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-navy-900/50 text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Risk per Share</p>
                    <p className="text-sm font-bold text-white font-mono">
                      ₹{result.risk_per_share}
                    </p>
                  </div>
                </div>
              </div>

              {/* Target & Profit */}
              <div className="glass-card p-6">
                <h4 className="text-sm font-semibold text-gray-300 mb-4">Profit Projection (2R Target)</h4>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Stop Loss</p>
                    <p className="text-lg font-bold text-coral-400 font-mono">
                      ₹{result.stop_loss_price}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">Entry</p>
                    <p className="text-lg font-bold text-white font-mono">
                      ₹{result.entry_price}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] text-gray-500 uppercase mb-1">2R Target</p>
                    <p className="text-lg font-bold text-emerald-400 font-mono">
                      ₹{result.target_price_2r}
                    </p>
                  </div>
                </div>

                {/* Visual price bar */}
                <div className="relative h-3 bg-navy-900 rounded-full mb-6">
                  <div className="absolute left-0 h-full w-1/3 bg-coral-500/30 rounded-l-full" />
                  <div className="absolute left-1/3 h-full w-2/3 bg-emerald-500/30 rounded-r-full" />
                  <div className="absolute left-1/3 top-1/2 w-3 h-3 bg-white rounded-full transform -translate-x-1/2 -translate-y-1/2 ring-2 ring-electric-500" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
                    <p className="text-[10px] text-emerald-500 uppercase mb-1">Potential Profit</p>
                    <p className="text-lg font-bold text-emerald-400 font-mono">
                      +{formatCurrency(result.potential_profit)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-electric-500/10 border border-electric-500/20 text-center">
                    <p className="text-[10px] text-electric-400 uppercase mb-1">Net P&L at Target</p>
                    <p className="text-lg font-bold text-electric-400 font-mono">
                      {formatCurrency(result.net_pnl_at_target)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Cost Breakdown */}
              <div className="glass-card p-6">
                <h4 className="text-sm font-semibold text-gray-300 mb-4">Estimated Transaction Costs</h4>
                <div className="space-y-2 text-sm">
                  {result.estimated_costs && typeof result.estimated_costs === 'object' && (
                    <>
                      {['at_target', 'at_stop'].map((scenario) => {
                        const data = (result.estimated_costs as Record<string, { gross_pnl: number; total_costs: number; net_pnl: number }>)[scenario];
                        if (!data) return null;
                        const isTarget = scenario === 'at_target';
                        return (
                          <div key={scenario} className="p-3 rounded-lg bg-navy-900/50">
                            <div className="flex justify-between items-center">
                              <span className="text-gray-400">
                                {isTarget ? '✅ At Target' : '🛑 At Stop Loss'}
                              </span>
                              <div className="text-right">
                                <span className={`font-mono font-semibold ${data.net_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                                  {data.net_pnl >= 0 ? '+' : ''}{formatCurrency(data.net_pnl)}
                                </span>
                                <span className="text-xs text-gray-500 ml-2">
                                  (costs: ₹{data.total_costs?.toFixed(0)})
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card p-12 text-center">
              <div className="text-6xl mb-4">🧮</div>
              <p className="text-gray-400 text-lg mb-2">Enter trade parameters</p>
              <p className="text-gray-500 text-sm">
                Calculate exact position size based on your risk budget and stop-loss distance
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
