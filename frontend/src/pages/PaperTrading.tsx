import { useState, useEffect, useCallback, useMemo } from 'react';
import Header from '../components/layout/Header';
import StockChartModal, { type StockChartData } from '../components/charts/StockChartModal';
import {
  paperTradingAPI,
  stocksAPI,
  type PaperAccount,
  type PaperPosition,
  type PaperOrder,
  type PaperQuote,
  type StockItem,
} from '../api/client';

const formatINR = (val: number) =>
  `₹${Math.abs(val).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export default function PaperTrading() {
  const [account, setAccount] = useState<PaperAccount | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [orders, setOrders] = useState<PaperOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'POSITIONS' | 'ORDERS' | 'ANALYTICS'>('POSITIONS');

  // Chart modal
  const [chartStock, setChartStock] = useState<StockChartData | null>(null);

  // Order modal state
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderSymbol, setOrderSymbol] = useState('');
  const [orderExchange, setOrderExchange] = useState<'NSE' | 'BSE'>('NSE');
  const [orderQuantity, setOrderQuantity] = useState<number>(10);
  const [orderPrice, setOrderPrice] = useState<string>('');
  const [orderStopLoss, setOrderStopLoss] = useState<string>('');
  const [orderTarget, setOrderTarget] = useState<string>('');
  const [orderNotes, setOrderNotes] = useState<string>('');
  const [submittingOrder, setSubmittingOrder] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orderSuccessMsg, setOrderSuccessMsg] = useState<string | null>(null);

  // Symbol search in order modal
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<StockItem[]>([]);
  const [searchingStocks, setSearchingStocks] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState<PaperQuote | null>(null);
  const [loadingQuote, setLoadingQuote] = useState(false);

  // Reset confirmation modal
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [resetting, setResetting] = useState(false);

  // Square off state
  const [squareOffPos, setSquareOffPos] = useState<PaperPosition | null>(null);
  const [closingPosId, setClosingPosId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!bannerMsg) return;
    const t = setTimeout(() => setBannerMsg(null), 5000);
    return () => clearTimeout(t);
  }, [bannerMsg]);

  // Load account data
  const fetchData = useCallback(async () => {
    try {
      const [acc, pos, ord] = await Promise.all([

        paperTradingAPI.getAccount(),
        paperTradingAPI.getPositions(),
        paperTradingAPI.getOrders(),
      ]);
      setAccount(acc);
      setPositions(pos);
      setOrders(ord);
    } catch (err) {
      console.error('Failed to load paper trading data', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  // Stock search debounce
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchingStocks(true);
      try {
        const res = await stocksAPI.list({ search: searchQuery.trim(), limit: 8 });
        setSearchResults(res.items || []);
      } catch (err) {
        console.error('Search error', err);
      } finally {
        setSearchingStocks(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // When a symbol is chosen, fetch live quote
  const handleSelectSymbol = async (symbol: string, companyName?: string) => {
    setOrderSymbol(symbol);
    setSearchQuery('');
    setSearchResults([]);
    setLoadingQuote(true);
    try {
      const quote = await paperTradingAPI.getQuote(symbol, orderExchange);
      if (companyName && !quote.company_name) {
        quote.company_name = companyName;
      }
      setSelectedQuote(quote);
      setOrderPrice(quote.current_price.toString());
      // Default recommended stop loss ~3% below, target ~6% above (1:2 R:R)
      const sl = Math.round(quote.current_price * 0.96 * 10) / 10;
      const tgt = Math.round(quote.current_price * 1.08 * 10) / 10;
      setOrderStopLoss(sl.toString());
      setOrderTarget(tgt.toString());
    } catch (err) {
      console.error('Quote error', err);
    } finally {
      setLoadingQuote(false);
    }
  };

  const openNewTradeModal = (prefillSymbol?: string, prefillSide: 'BUY' | 'SELL' = 'BUY', prefillQty?: number) => {
    setOrderSide(prefillSide);
    setOrderError(null);
    setOrderSuccessMsg(null);
    setOrderNotes('');
    setOrderQuantity(prefillQty && prefillQty > 0 ? prefillQty : 10);
    if (prefillSymbol) {
      handleSelectSymbol(prefillSymbol);
    } else {
      setOrderSymbol('');
      setSelectedQuote(null);
      setOrderPrice('');
      setOrderStopLoss('');
      setOrderTarget('');
    }
    setIsOrderModalOpen(true);
  };


  // Quick cash allocation buttons for quantity
  const handleAllocateCash = (pct: number) => {
    if (!account || !selectedQuote || selectedQuote.current_price <= 0) return;
    const targetCash = account.cash_balance * (pct / 100);
    const qty = Math.floor(targetCash / selectedQuote.current_price);
    setOrderQuantity(Math.max(1, qty));
  };

  // Estimated charges
  const estimatedTurnover = useMemo(() => {
    const p = parseFloat(orderPrice) || (selectedQuote?.current_price ?? 0);
    return p * orderQuantity;
  }, [orderPrice, selectedQuote, orderQuantity]);

  const estimatedCharges = useMemo(() => {
    if (estimatedTurnover <= 0) return 0;
    const brokerage = 20.0;
    const stt = estimatedTurnover * 0.001;
    const exchangeCharge = estimatedTurnover * 0.0000345;
    const sebiFee = estimatedTurnover * 0.000001;
    const stampDuty = orderSide === 'BUY' ? estimatedTurnover * 0.00015 : 0;
    const gst = (brokerage + exchangeCharge + sebiFee) * 0.18;
    return Math.round((brokerage + stt + exchangeCharge + sebiFee + stampDuty + gst) * 100) / 100;
  }, [estimatedTurnover, orderSide]);

  // Risk-Reward ratio
  const riskRewardRatio = useMemo(() => {
    const entry = parseFloat(orderPrice) || selectedQuote?.current_price;
    const sl = parseFloat(orderStopLoss);
    const tgt = parseFloat(orderTarget);
    if (!entry || !sl || !tgt || entry <= sl || tgt <= entry) return null;
    const risk = entry - sl;
    const reward = tgt - entry;
    return (reward / risk).toFixed(1);
  }, [orderPrice, selectedQuote, orderStopLoss, orderTarget]);

  // Submit Order
  const handleExecuteOrder = async () => {
    if (!orderSymbol) {
      setOrderError('Please select a stock symbol');
      return;
    }
    if (orderQuantity <= 0) {
      setOrderError('Quantity must be greater than 0');
      return;
    }
    setSubmittingOrder(true);
    setOrderError(null);

    try {
      const priceNum = parseFloat(orderPrice);
      await paperTradingAPI.placeOrder({
        symbol: orderSymbol,
        exchange: orderExchange,
        order_side: orderSide,
        order_type: 'MARKET',
        quantity: orderQuantity,
        price: !isNaN(priceNum) && priceNum > 0 ? priceNum : undefined,
        stop_loss: orderStopLoss ? parseFloat(orderStopLoss) : undefined,
        target_price: orderTarget ? parseFloat(orderTarget) : undefined,
        notes: orderNotes.trim() || undefined,
      });

      setOrderSuccessMsg(
        `Executed ${orderSide} ${orderQuantity} shares of ${orderSymbol} successfully!`
      );
      await fetchData();
      setTimeout(() => {
        setIsOrderModalOpen(false);
        setOrderSuccessMsg(null);
      }, 1200);
    } catch (err: any) {
      setOrderError(err.message || 'Failed to execute trade');
    } finally {
      setSubmittingOrder(false);
    }
  };

  // Square off position handlers
  const handleSquareOff = (pos: PaperPosition) => {
    setActionError(null);
    setSquareOffPos(pos);
  };

  const confirmSquareOff = async () => {
    if (!squareOffPos) return;
    setClosingPosId(squareOffPos.id);
    setActionError(null);
    try {
      const res = await paperTradingAPI.closePosition(squareOffPos.id);
      const exitP = res.price || squareOffPos.current_price || squareOffPos.avg_price;
      const realized = res.realized_pnl ?? 0;
      setBannerMsg({
        type: 'success',
        text: `⚡ Squared off ${squareOffPos.quantity} shares of ${squareOffPos.symbol} at ₹${exitP.toFixed(2)}. Realized P&L: ${realized >= 0 ? '+' : '-'}₹${Math.abs(realized).toFixed(2)}`,
      });
      setSquareOffPos(null);
      await fetchData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to square off position');
    } finally {
      setClosingPosId(null);
    }
  };

  // Reset Account
  const handleResetConfirm = async () => {
    setResetting(true);
    setActionError(null);
    try {
      await paperTradingAPI.resetAccount();
      await fetchData();
      setIsResetModalOpen(false);
      setBannerMsg({
        type: 'success',
        text: 'Account successfully reset to ₹10,00,000 virtual balance.',
      });
    } catch (err: any) {
      setActionError(err.message || 'Failed to reset account');
    } finally {
      setResetting(false);
    }
  };


  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <div className="w-12 h-12 border-4 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
        <span className="text-sm text-gray-400">Loading Paper Trading Account...</span>
      </div>
    );
  }

  const isNetPositive = (account?.net_pnl ?? 0) >= 0;
  const isUnrealizedPositive = (account?.unrealized_pnl ?? 0) >= 0;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Banner Notification */}
      {bannerMsg && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between shadow-lg animate-fade-in ${
            bannerMsg.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : 'bg-coral-500/15 border-coral-500/30 text-coral-300'
          }`}
        >
          <div className="flex items-center gap-2.5 font-medium text-sm">
            <span>{bannerMsg.type === 'success' ? '✅' : '⚠️'}</span>
            <span>{bannerMsg.text}</span>
          </div>
          <button
            onClick={() => setBannerMsg(null)}
            className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded bg-navy-900/60"
          >
            ✕
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Header
          title="Paper Trading"
          subtitle="Simulated swing trading with virtual capital & live market quotes"
        />

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3.5 py-2 rounded-xl bg-navy-800 hover:bg-navy-700 text-gray-300 hover:text-white border border-navy-700 transition flex items-center gap-2 text-sm"
            title="Refresh Quotes and Prices"
          >
            <span className={refreshing ? 'animate-spin' : ''}>🔄</span>
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <button
            onClick={() => setIsResetModalOpen(true)}
            className="px-3.5 py-2 rounded-xl bg-coral-500/10 hover:bg-coral-500/20 text-coral-400 border border-coral-500/30 transition text-sm flex items-center gap-1.5"
            title="Reset to ₹10,00,000 Initial Capital"
          >
            <span>⚠️</span>
            <span>Reset Account</span>
          </button>
          <button
            onClick={() => openNewTradeModal()}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-electric-500 to-emerald-500 hover:from-electric-600 hover:to-emerald-600 text-white font-medium text-sm shadow-lg shadow-electric-500/20 transition flex items-center gap-2"
          >
            <span className="text-base font-bold">+</span>
            <span>New Trade</span>
          </button>
        </div>
      </div>

      {/* Account Overview Cards */}
      {account && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          <div className="metric-card">
            <span className="metric-label">Portfolio Value</span>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className="metric-value text-white">{formatINR(account.total_portfolio_value)}</span>
            </div>
            <span className={`text-xs font-mono font-medium ${isNetPositive ? 'text-emerald-400' : 'text-coral-400'}`}>
              {isNetPositive ? '+' : '-'}{formatINR(account.net_pnl)} ({isNetPositive ? '+' : ''}{account.net_return_pct.toFixed(2)}%)
            </span>
          </div>

          <div className="metric-card">
            <span className="metric-label">Cash Available</span>
            <span className="metric-value text-emerald-400 mt-1">{formatINR(account.cash_balance)}</span>
            <span className="text-[11px] text-gray-500">Unallocated Capital</span>
          </div>

          <div className="metric-card">
            <span className="metric-label">Invested Capital</span>
            <span className="metric-value text-electric-400 mt-1">{formatINR(account.invested_capital)}</span>
            <span className="text-[11px] text-gray-500">{account.open_positions_count} Open Positions</span>
          </div>

          <div className="metric-card">
            <span className="metric-label">Unrealized P&L</span>
            <span className={`metric-value mt-1 ${isUnrealizedPositive ? 'text-emerald-400' : 'text-coral-400'}`}>
              {isUnrealizedPositive ? '+' : '-'}{formatINR(account.unrealized_pnl)}
            </span>
            <span className={`text-[11px] font-mono ${isUnrealizedPositive ? 'text-emerald-400' : 'text-coral-400'}`}>
              {isUnrealizedPositive ? '+' : ''}{account.unrealized_pnl_pct.toFixed(2)}%
            </span>
          </div>

          <div className="metric-card">
            <span className="metric-label">Realized P&L</span>
            <span className={`metric-value mt-1 ${account.realized_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
              {account.realized_pnl >= 0 ? '+' : '-'}{formatINR(account.realized_pnl)}
            </span>
            <span className="text-[11px] text-gray-500">From Closed Trades</span>
          </div>

          <div className="metric-card">
            <span className="metric-label">Win Rate / Trades</span>
            <span className="metric-value text-amber-400 mt-1">
              {account.total_trades_count > 0 ? `${account.win_rate_pct}%` : '—'}
            </span>
            <span className="text-[11px] text-gray-400 font-mono">
              {account.winning_trades_count}W • {account.losing_trades_count}L ({account.total_trades_count} orders)
            </span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-navy-800 pb-3">
        <button
          onClick={() => setActiveTab('POSITIONS')}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'POSITIONS'
              ? 'bg-electric-500/15 text-electric-400 border border-electric-500/30 shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <span>💼 Open Positions</span>
          <span className="px-1.5 py-0.5 text-xs rounded-full bg-navy-800 text-gray-300 font-mono">
            {positions.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('ORDERS')}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'ORDERS'
              ? 'bg-electric-500/15 text-electric-400 border border-electric-500/30 shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <span>📋 Order History</span>
          <span className="px-1.5 py-0.5 text-xs rounded-full bg-navy-800 text-gray-300 font-mono">
            {orders.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('ANALYTICS')}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'ANALYTICS'
              ? 'bg-electric-500/15 text-electric-400 border border-electric-500/30 shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <span>📊 Performance & Taxes</span>
        </button>
      </div>

      {/* TAB 1: POSITIONS */}
      {activeTab === 'POSITIONS' && (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Exchange</th>
                  <th>Quantity</th>
                  <th>Avg Buy Price</th>
                  <th>Current Price</th>
                  <th>Invested</th>
                  <th>Current Value</th>
                  <th>Unrealized P&L</th>
                  <th>Stop Loss</th>
                  <th>Target</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="text-center py-12 text-gray-500">
                      <div className="flex flex-col items-center gap-3">
                        <span className="text-4xl">🎯</span>
                        <p className="text-base font-medium text-gray-400">No active paper trading positions</p>
                        <p className="text-xs text-gray-500 max-w-md">
                          Deploy your ₹10,00,000 virtual capital to test Indian swing setups without financial risk.
                        </p>
                        <button
                          onClick={() => openNewTradeModal()}
                          className="mt-2 px-4 py-2 rounded-xl bg-electric-500 text-white text-xs font-semibold hover:bg-electric-600 transition"
                        >
                          + Place First Paper Trade
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  positions.map((pos) => {
                    const isPosPositive = pos.unrealized_pnl >= 0;
                    return (
                      <tr key={pos.id} className="hover:bg-navy-800/40 transition">
                        <td>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                setChartStock({
                                  symbol: pos.symbol,
                                  current_price: pos.current_price,
                                })
                              }
                              className="font-semibold text-white hover:text-electric-400 hover:underline transition flex items-center gap-1.5 group"
                              title="Inspect Candlestick Chart"
                            >
                              <span>{pos.symbol}</span>
                              <span className="text-xs text-electric-400 opacity-60 group-hover:opacity-100 transition">
                                📊
                              </span>
                            </button>
                          </div>
                          {pos.notes && (
                            <p className="text-[10px] text-gray-500 truncate max-w-[140px]" title={pos.notes}>
                              {pos.notes}
                            </p>
                          )}
                        </td>
                        <td>
                          <span className="text-xs px-2 py-0.5 rounded bg-navy-800 text-gray-400 font-mono">
                            {pos.exchange}
                          </span>
                        </td>
                        <td className="font-mono font-medium">{pos.quantity}</td>
                        <td className="font-mono">₹{pos.avg_price.toFixed(2)}</td>
                        <td className="font-mono font-semibold text-white">
                          ₹{pos.current_price ? pos.current_price.toFixed(2) : '—'}
                        </td>
                        <td className="font-mono text-gray-300">{formatINR(pos.invested_value)}</td>
                        <td className="font-mono text-white">{formatINR(pos.current_value)}</td>
                        <td>
                          <div className="flex flex-col">
                            <span
                              className={`font-mono font-bold text-sm ${
                                isPosPositive ? 'text-emerald-400' : 'text-coral-400'
                              }`}
                            >
                              {isPosPositive ? '+' : '-'}{formatINR(pos.unrealized_pnl)}
                            </span>
                            <span
                              className={`text-[11px] font-mono ${
                                isPosPositive ? 'text-emerald-400/80' : 'text-coral-400/80'
                              }`}
                            >
                              {isPosPositive ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                            </span>
                          </div>
                        </td>
                        <td className="font-mono text-coral-400">
                          {pos.stop_loss ? `₹${pos.stop_loss.toFixed(1)}` : '—'}
                        </td>
                        <td className="font-mono text-emerald-400">
                          {pos.target_price ? `₹${pos.target_price.toFixed(1)}` : '—'}
                        </td>
                        <td className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => openNewTradeModal(pos.symbol, 'SELL', pos.quantity)}
                              className="px-2.5 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-xs text-gray-300 hover:text-white transition"
                              title="Sell or Partial Exit"
                            >
                              Sell
                            </button>
                            <button
                              onClick={() => handleSquareOff(pos)}
                              disabled={closingPosId === pos.id}
                              className="px-2.5 py-1.5 rounded-lg bg-coral-500/20 hover:bg-coral-500/30 text-coral-400 border border-coral-500/40 text-xs font-semibold transition flex items-center gap-1 shadow-sm active:scale-95 cursor-pointer"
                              title="Square off position at market price"
                            >
                              {closingPosId === pos.id ? (
                                <span className="animate-spin text-xs">⌛</span>
                              ) : (
                                <span>⚡ Square Off</span>
                              )}
                            </button>
                          </div>
                        </td>

                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: ORDER HISTORY */}
      {activeTab === 'ORDERS' && (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date & Time</th>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Qty</th>
                  <th>Executed Price</th>
                  <th>Turnover</th>
                  <th>Charges</th>
                  <th>Realized P&L</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {orders.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="text-center py-10 text-gray-500">
                      No executed paper trades yet
                    </td>
                  </tr>
                ) : (
                  orders.map((ord) => {
                    const isBuy = ord.order_side === 'BUY';
                    const isPositive = (ord.realized_pnl || 0) >= 0;
                    return (
                      <tr key={ord.id} className="hover:bg-navy-800/40 transition">
                        <td className="text-xs text-gray-400 font-mono">
                          {new Date(ord.created_at).toLocaleString('en-IN', {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </td>
                        <td>
                          <button
                            onClick={() =>
                              setChartStock({
                                symbol: ord.symbol,
                                current_price: ord.price,
                              })
                            }
                            className="font-semibold text-white hover:text-electric-400 hover:underline transition flex items-center gap-1 group"
                          >
                            <span>{ord.symbol}</span>
                            <span className="text-[10px] text-gray-500">{ord.exchange}</span>
                          </button>
                        </td>
                        <td>
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              isBuy
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                : 'bg-coral-500/15 text-coral-400 border border-coral-500/30'
                            }`}
                          >
                            {ord.order_side}
                          </span>
                        </td>
                        <td className="font-mono font-medium">{ord.quantity}</td>
                        <td className="font-mono">₹{ord.price.toFixed(2)}</td>
                        <td className="font-mono text-gray-300">
                          {formatINR(ord.price * ord.quantity)}
                        </td>
                        <td className="font-mono text-xs text-gray-400">
                          ₹{(ord.charges || 0).toFixed(2)}
                        </td>
                        <td>
                          {ord.order_side === 'SELL' ? (
                            <span
                              className={`font-mono font-bold text-xs ${
                                isPositive ? 'text-emerald-400' : 'text-coral-400'
                              }`}
                            >
                              {isPositive ? '+' : '-'}{formatINR(ord.realized_pnl || 0)}
                              <span className="text-[10px] ml-1 opacity-80">
                                ({isPositive ? '+' : ''}{(ord.pnl_pct || 0).toFixed(1)}%)
                              </span>
                            </span>
                          ) : (
                            <span className="text-gray-500 text-xs">—</span>
                          )}
                        </td>
                        <td>
                          <span className="badge-open text-[11px]">{ord.status}</span>
                        </td>
                        <td className="text-xs text-gray-400 max-w-xs truncate" title={ord.notes || ''}>
                          {ord.notes || '—'}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: PERFORMANCE & TAXES */}
      {activeTab === 'ANALYTICS' && account && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>🎯</span>
              <span>Trading Statistics</span>
            </h3>
            <div className="space-y-3 divide-y divide-navy-800">
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Starting Capital</span>
                <span className="font-mono font-semibold text-white">{formatINR(account.initial_capital)}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Current Capital (Net Worth)</span>
                <span className="font-mono font-semibold text-emerald-400">
                  {formatINR(account.total_portfolio_value)}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Total Orders Executed</span>
                <span className="font-mono text-white">{account.total_trades_count}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Winning Trades</span>
                <span className="font-mono text-emerald-400 font-semibold">{account.winning_trades_count}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Losing Trades</span>
                <span className="font-mono text-coral-400 font-semibold">{account.losing_trades_count}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Win Rate %</span>
                <span className="font-mono font-bold text-amber-400">
                  {account.win_rate_pct.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          <div className="glass-card p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>🧾</span>
              <span>Indian Regulatory Charges Incurred</span>
            </h3>
            <p className="text-xs text-gray-400">
              TradeLab accurately simulates all Indian equity transaction friction (Brokerage, STT, Exchange charges, SEBI fee, Stamp duty, and GST).
            </p>
            <div className="space-y-3 divide-y divide-navy-800">
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Total Friction / Fees Paid</span>
                <span className="font-mono font-semibold text-coral-400">
                  {formatINR(account.total_charges_paid)}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Gross Realized P&L</span>
                <span className="font-mono text-white">
                  {formatINR(account.realized_pnl + account.total_charges_paid)}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Net Realized P&L (Post Charges)</span>
                <span
                  className={`font-mono font-bold ${
                    account.realized_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'
                  }`}
                >
                  {account.realized_pnl >= 0 ? '+' : '-'}{formatINR(account.realized_pnl)}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-sm text-gray-400">Active Positions Exposure</span>
                <span className="font-mono text-electric-400 font-semibold">
                  {formatINR(account.invested_capital)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ORDER EXECUTION */}
      {isOrderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-card bg-navy-900 border border-navy-700 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-navy-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">📈</span>
                <h3 className="text-lg font-bold text-white">Execute Paper Trade</h3>
              </div>
              <button
                onClick={() => setIsOrderModalOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg bg-navy-800 transition"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto flex-1">
              {/* Buy / Sell Toggle */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-navy-950 rounded-xl border border-navy-800">
                <button
                  type="button"
                  onClick={() => setOrderSide('BUY')}
                  className={`py-2 rounded-lg text-sm font-bold transition ${
                    orderSide === 'BUY'
                      ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  BUY (Long)
                </button>
                <button
                  type="button"
                  onClick={() => setOrderSide('SELL')}
                  className={`py-2 rounded-lg text-sm font-bold transition ${
                    orderSide === 'SELL'
                      ? 'bg-coral-500 text-white shadow-lg shadow-coral-500/25'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  SELL (Exit)
                </button>
              </div>

              {/* Stock Symbol Selection */}
              <div className="space-y-1.5 relative">
                <label className="text-xs font-semibold text-gray-300">Stock Symbol (NSE / BSE)</label>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      placeholder="Search company (e.g. RELIANCE, TATASTEEL)..."
                      value={orderSymbol || searchQuery}
                      onChange={(e) => {
                        setOrderSymbol('');
                        setSelectedQuote(null);
                        setSearchQuery(e.target.value);
                      }}
                      className="w-full bg-navy-950 border border-navy-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-electric-500 uppercase font-mono"
                    />
                    {searchingStocks && (
                      <span className="absolute right-3 top-3 text-xs text-gray-400 animate-spin">
                        ⏳
                      </span>
                    )}
                  </div>
                  <select
                    value={orderExchange}
                    onChange={(e) => setOrderExchange(e.target.value as 'NSE' | 'BSE')}
                    className="bg-navy-950 border border-navy-700 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-electric-500"
                  >
                    <option value="NSE">NSE</option>
                    <option value="BSE">BSE</option>
                  </select>
                </div>

                {/* Autocomplete Dropdown */}
                {searchResults.length > 0 && (
                  <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-navy-900 border border-navy-700 rounded-xl shadow-xl overflow-hidden max-h-48 overflow-y-auto">
                    {searchResults.map((s) => {
                      const sym = s.nse_symbol || s.bse_symbol || '';
                      return (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => handleSelectSymbol(sym, s.company_name)}
                          className="w-full text-left px-3.5 py-2 hover:bg-navy-800 transition flex items-center justify-between border-b border-navy-800/50 last:border-0"
                        >
                          <div>
                            <span className="font-mono font-bold text-white text-sm">{sym}</span>
                            <span className="text-xs text-gray-400 ml-2 truncate max-w-[200px] inline-block align-bottom">
                              {s.company_name}
                            </span>
                          </div>
                          <span className="text-[10px] text-gray-500">{s.category || 'Equity'}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Quote Snapshot Card */}
              {loadingQuote ? (
                <div className="p-3 bg-navy-950/60 rounded-xl border border-navy-800 text-center text-xs text-gray-400">
                  Fetching live market quote...
                </div>
              ) : selectedQuote ? (
                <div className="p-3.5 bg-navy-950/80 rounded-xl border border-navy-800 flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-white text-sm">{selectedQuote.symbol}</h4>
                    <p className="text-[11px] text-gray-400 truncate max-w-[220px]">
                      {selectedQuote.company_name}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-bold font-mono text-white">
                      ₹{selectedQuote.current_price.toFixed(2)}
                    </span>
                    <p
                      className={`text-xs font-mono font-medium ${
                        (selectedQuote.change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-coral-400'
                      }`}
                    >
                      {(selectedQuote.change_pct ?? 0) >= 0 ? '+' : ''}
                      {(selectedQuote.change_pct ?? 0).toFixed(2)}%
                    </p>
                  </div>
                </div>
              ) : null}

              {/* Quantity & Quick Allocators */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-gray-300">Quantity (Shares)</label>
                  {orderSide === 'BUY' && account && (
                    <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
                      <span>Quick % Cash:</span>
                      <button
                        type="button"
                        onClick={() => handleAllocateCash(10)}
                        className="px-1.5 py-0.5 rounded bg-navy-800 hover:bg-navy-700 text-electric-400 font-mono transition"
                      >
                        10%
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAllocateCash(25)}
                        className="px-1.5 py-0.5 rounded bg-navy-800 hover:bg-navy-700 text-electric-400 font-mono transition"
                      >
                        25%
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAllocateCash(50)}
                        className="px-1.5 py-0.5 rounded bg-navy-800 hover:bg-navy-700 text-electric-400 font-mono transition"
                      >
                        50%
                      </button>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setOrderQuantity(Math.max(1, orderQuantity - 5))}
                    className="w-10 h-10 rounded-xl bg-navy-800 text-gray-200 hover:text-white font-bold transition flex items-center justify-center text-base"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    min={1}
                    value={orderQuantity || ''}
                    onChange={(e) => setOrderQuantity(parseInt(e.target.value) || 0)}
                    className="flex-1 text-center bg-navy-950 border border-navy-700 rounded-xl px-3.5 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-electric-500 font-semibold"
                  />
                  <button
                    type="button"
                    onClick={() => setOrderQuantity(orderQuantity + 5)}
                    className="w-10 h-10 rounded-xl bg-navy-800 text-gray-200 hover:text-white font-bold transition flex items-center justify-center text-base"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Execution Price */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">
                  Execution Price (₹) <span className="text-gray-500 font-normal">(Market order)</span>
                </label>
                <input
                  type="number"
                  step="0.05"
                  value={orderPrice}
                  onChange={(e) => setOrderPrice(e.target.value)}
                  placeholder="Market Price"
                  className="w-full bg-navy-950 border border-navy-700 rounded-xl px-3.5 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-electric-500"
                />
              </div>

              {/* Stop Loss & Target Price */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-coral-400">Stop Loss (₹)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={orderStopLoss}
                    onChange={(e) => setOrderStopLoss(e.target.value)}
                    placeholder="Optional SL"
                    className="w-full bg-navy-950 border border-coral-500/30 rounded-xl px-3.5 py-2 text-sm font-mono text-white focus:outline-none focus:border-coral-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-emerald-400">Target (₹)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={orderTarget}
                    onChange={(e) => setOrderTarget(e.target.value)}
                    placeholder="Optional Target"
                    className="w-full bg-navy-950 border border-emerald-500/30 rounded-xl px-3.5 py-2 text-sm font-mono text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Risk-Reward Badge */}
              {riskRewardRatio && (
                <div className="p-2 rounded-lg bg-navy-950/60 border border-navy-800 flex items-center justify-between text-xs">
                  <span className="text-gray-400">Planned Risk:Reward</span>
                  <span className="font-mono font-bold text-amber-400">1 : {riskRewardRatio}</span>
                </div>
              )}

              {/* Notes / Rationale */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">
                  Trade Rationale / Journal Notes
                </label>
                <input
                  type="text"
                  placeholder="e.g. 50-EMA bounce with 2x volume expansion..."
                  value={orderNotes}
                  onChange={(e) => setOrderNotes(e.target.value)}
                  className="w-full bg-navy-950 border border-navy-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-electric-500"
                />
              </div>

              {/* Financial Summary */}
              <div className="p-3.5 bg-navy-950 rounded-xl border border-navy-800 space-y-2 text-xs">
                <div className="flex justify-between text-gray-400">
                  <span>Order Value</span>
                  <span className="font-mono text-white">{formatINR(estimatedTurnover)}</span>
                </div>
                <div className="flex justify-between text-gray-400">
                  <span>Est. Friction / Charges (STT, GST, etc.)</span>
                  <span className="font-mono text-coral-400">₹{estimatedCharges.toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-bold pt-1.5 border-t border-navy-800 text-white">
                  <span>Total Capital Required</span>
                  <span className="font-mono text-emerald-400">
                    {formatINR(estimatedTurnover + (orderSide === 'BUY' ? estimatedCharges : 0))}
                  </span>
                </div>
              </div>

              {/* Error or Success Notice */}
              {orderError && (
                <div className="p-3 rounded-xl bg-coral-500/15 border border-coral-500/30 text-coral-400 text-xs flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{orderError}</span>
                </div>
              )}

              {orderSuccessMsg && (
                <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                  <span>✅</span>
                  <span>{orderSuccessMsg}</span>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-navy-800 bg-navy-900 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsOrderModalOpen(false)}
                className="px-4 py-2 rounded-xl text-gray-400 hover:text-white text-sm transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingOrder || !orderSymbol}
                onClick={handleExecuteOrder}
                className={`px-6 py-2.5 rounded-xl font-bold text-sm text-white transition flex items-center gap-2 shadow-lg ${
                  orderSide === 'BUY'
                    ? 'bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/25 disabled:opacity-50'
                    : 'bg-coral-500 hover:bg-coral-600 shadow-coral-500/25 disabled:opacity-50'
                }`}
              >
                {submittingOrder ? (
                  <>
                    <span className="animate-spin text-xs">⏳</span>
                    <span>Executing...</span>
                  </>
                ) : (
                  <span>Execute {orderSide} Order</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SQUARE OFF CONFIRMATION */}
      {squareOffPos && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-card bg-navy-900 border border-coral-500/30 max-w-md w-full p-6 rounded-2xl space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-coral-400">
                <span className="text-2xl">⚡</span>
                <h3 className="text-lg font-bold text-white">Square Off Position</h3>
              </div>
              <button
                onClick={() => setSquareOffPos(null)}
                className="text-gray-400 hover:text-white p-1 rounded-lg bg-navy-800 transition"
              >
                ✕
              </button>
            </div>

            <p className="text-sm text-gray-300">
              Are you sure you want to exit all <strong className="text-white font-mono">{squareOffPos.quantity}</strong> shares of <strong className="text-white font-mono">{squareOffPos.symbol}</strong> at market price?
            </p>

            <div className="p-3.5 bg-navy-950 rounded-xl border border-navy-800 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-gray-400">
                <span>Avg Buy Price:</span>
                <span className="text-white">₹{squareOffPos.avg_price.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Current Market Price:</span>
                <span className="text-white font-semibold">₹{squareOffPos.current_price?.toFixed(2) || '—'}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Estimated Exit Value:</span>
                <span className="text-emerald-400 font-semibold">{formatINR((squareOffPos.current_price || squareOffPos.avg_price) * squareOffPos.quantity)}</span>
              </div>
              <div className="flex justify-between text-gray-400 pt-1.5 border-t border-navy-800">
                <span>Unrealized P&L:</span>
                <span className={`font-bold ${squareOffPos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
                  {squareOffPos.unrealized_pnl >= 0 ? '+' : '-'}{formatINR(squareOffPos.unrealized_pnl)} ({squareOffPos.unrealized_pnl_pct.toFixed(2)}%)
                </span>
              </div>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-coral-500/15 border border-coral-500/30 text-coral-400 text-xs">
                ⚠️ {actionError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setSquareOffPos(null)}
                disabled={closingPosId !== null}
                className="px-4 py-2 rounded-xl text-gray-400 hover:text-white text-sm transition"
              >
                Cancel
              </button>
              <button
                onClick={() => confirmSquareOff()}
                disabled={closingPosId !== null}
                className="px-5 py-2.5 rounded-xl bg-coral-500 hover:bg-coral-600 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-coral-500/25 cursor-pointer"
              >
                {closingPosId !== null ? (
                  <>
                    <span className="animate-spin text-xs">⏳</span>
                    <span>Closing Position...</span>
                  </>
                ) : (
                  <span>Confirm Square Off</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: RESET ACCOUNT CONFIRMATION */}
      {isResetModalOpen && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-card bg-navy-900 border border-coral-500/30 max-w-md w-full p-6 rounded-2xl space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-coral-400">
              <span className="text-3xl">⚠️</span>
              <h3 className="text-lg font-bold text-white">Reset Paper Trading Account?</h3>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">
              This will reset your virtual capital back to <strong className="text-emerald-400">₹10,00,000.00</strong> and permanently wipe all open positions and order history.
            </p>
            <div className="p-3 bg-navy-950 rounded-xl text-xs text-gray-400">
              Use this when you want to start a fresh swing trading experiment or test a brand-new strategy.
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setIsResetModalOpen(false)}
                className="px-4 py-2 rounded-xl text-gray-400 hover:text-white text-sm transition"
              >
                Cancel
              </button>
              <button
                disabled={resetting}
                onClick={handleResetConfirm}
                className="px-5 py-2 rounded-xl bg-coral-500 hover:bg-coral-600 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-coral-500/20"
              >
                {resetting ? 'Resetting...' : 'Yes, Reset to ₹10 Lakhs'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Stock Candlestick Modal */}
      <StockChartModal
        isOpen={!!chartStock}
        onClose={() => setChartStock(null)}
        stock={chartStock}
      />
    </div>
  );
}
