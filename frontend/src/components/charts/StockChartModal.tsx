import { useEffect, useRef, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  AreaSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
} from 'lightweight-charts';
import { stocksAPI, type StockCandlesResponse, type CandleData } from '../../api/client';

export interface StockChartData {
  symbol: string;
  company_name?: string;
  current_price?: number | null;
  listing_price?: number | null;
  return_since_listing_pct?: number | null;
  category?: string;
  listing_date?: string;
  days_since_listing?: number;
  operating_profit_cr?: number | null;
  operating_profit_growth_pct?: number | null;
  is_relisted?: boolean;
}

interface StockChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  stock: StockChartData | null;
}

type Period = '1mo' | '3mo' | '6mo' | '1y' | 'max';
type ChartStyle = 'candles' | 'area';
type Exchange = 'NSE' | 'BSE';
type CandleInterval = '1d' | '1wk' | '1mo';

// TradingView standard colors
const TV_GREEN = '#089981';
const TV_RED = '#f23645';
const TV_GREEN_VOL = 'rgba(8, 153, 129, 0.45)';
const TV_RED_VOL = 'rgba(242, 54, 69, 0.45)';

export default function StockChartModal({ isOpen, onClose, stock }: StockChartModalProps) {
  // Maximize / Fullscreen state
  const [isMaximized, setIsMaximized] = useState(false);

  // Candle Interval: Daily (Default), Weekly, Monthly
  const [candleInterval, setCandleInterval] = useState<CandleInterval>('1d');
  const [period, setPeriod] = useState<Period>('1y');
  const [exchange, setExchange] = useState<Exchange>('NSE');
  const [chartStyle, setChartStyle] = useState<ChartStyle>('candles');
  const [showEma20, setShowEma20] = useState(true);
  const [showEma50, setShowEma50] = useState(true);

  // Data state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candleData, setCandleData] = useState<StockCandlesResponse | null>(null);
  const [hoveredCandle, setHoveredCandle] = useState<CandleData | null>(null);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const ema20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ema50SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Keyboard shortcuts: Escape to close/unmaximize, F to toggle fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        if (isMaximized) {
          setIsMaximized(false);
        } else {
          onClose();
        }
      } else if (e.key === 'f' || e.key === 'F') {
        const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
        if (tag !== 'input' && tag !== 'textarea') {
          setIsMaximized((prev) => !prev);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isMaximized, onClose]);

  // Fetch candle data from backend
  useEffect(() => {
    if (!isOpen || !stock) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    stocksAPI
      .getCandles(stock.symbol, { exchange, period, interval: candleInterval })
      .then((data) => {
        if (!isMounted) return;
        setCandleData(data);
        setHoveredCandle(null);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load candles:', err);
        setError(err.message || 'Failed to download price data for this stock.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, stock?.symbol, period, exchange, candleInterval]);

  // Render TradingView Lightweight Chart
  useEffect(() => {
    if (!isOpen || !chartContainerRef.current || !candleData || candleData.candles.length === 0) {
      return;
    }

    const container = chartContainerRef.current;

    // Clean up previous instance
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 450;

    // Create chart matching TradingView exact layout
    const chart = createChart(container, {
      width,
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#0a0f1d' },
        textColor: '#94a3b8',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(30, 41, 59, 0.45)' },
        horzLines: { color: 'rgba(30, 41, 59, 0.45)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#4f6cf7',
          width: 1,
          style: 3,
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: '#4f6cf7',
          width: 1,
          style: 3,
          labelBackgroundColor: '#1e293b',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
        autoScale: true,
        scaleMargins: {
          top: 0.08,
          bottom: 0.22, // 22% room for volume at bottom
        },
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
        timeVisible: false,
        rightOffset: 8, // TradingView right margin
        barSpacing: 9,
        minBarSpacing: 3,
      },
    });

    chartInstanceRef.current = chart;

    // 1. Candlestick Series (TradingView styling)
    if (chartStyle === 'candles') {
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: TV_GREEN,
        downColor: TV_RED,
        borderVisible: true,
        borderUpColor: TV_GREEN,
        borderDownColor: TV_RED,
        wickVisible: true,
        wickUpColor: TV_GREEN,
        wickDownColor: TV_RED,
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.05,
        },
      });

      candleSeries.setData(
        candleData.candles.map((c) => ({
          time: c.time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );
      candleSeriesRef.current = candleSeries;
    } else {
      const areaSeries = chart.addSeries(AreaSeries, {
        topColor: 'rgba(8, 153, 129, 0.4)',
        bottomColor: 'rgba(8, 153, 129, 0.01)',
        lineColor: TV_GREEN,
        lineWidth: 2,
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.05,
        },
      });
      areaSeries.setData(
        candleData.candles.map((c) => ({
          time: c.time,
          value: c.close,
        }))
      );
      areaSeriesRef.current = areaSeries;
    }

    // 2. Volume Histogram (Bottom 22% pane)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '', // Separate scale
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.78, // Bottom 22%
        bottom: 0,
      },
    });
    volumeSeries.setData(
      candleData.candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? TV_GREEN_VOL : TV_RED_VOL,
      }))
    );
    volumeSeriesRef.current = volumeSeries;

    // 3. 20 EMA Line
    if (showEma20) {
      const validEma20 = candleData.candles.filter((c) => c.ema20 !== null && c.ema20 !== undefined);
      if (validEma20.length > 0) {
        const ema20Series = chart.addSeries(LineSeries, {
          color: '#38bdf8', // Sky blue
          lineWidth: 2,
          title: '20 EMA',
          priceFormat: { type: 'price', precision: 2, minMove: 0.05 },
        });
        ema20Series.setData(
          validEma20.map((c) => ({
            time: c.time,
            value: c.ema20 as number,
          }))
        );
        ema20SeriesRef.current = ema20Series;
      }
    }

    // 4. 50 EMA Line
    if (showEma50) {
      const validEma50 = candleData.candles.filter((c) => c.ema50 !== null && c.ema50 !== undefined);
      if (validEma50.length > 0) {
        const ema50Series = chart.addSeries(LineSeries, {
          color: '#c084fc', // Purple
          lineWidth: 2,
          title: '50 EMA',
          priceFormat: { type: 'price', precision: 2, minMove: 0.05 },
        });
        ema50Series.setData(
          validEma50.map((c) => ({
            time: c.time,
            value: c.ema50 as number,
          }))
        );
        ema50SeriesRef.current = ema50Series;
      }
    }

    // Fit content smoothly with right offset
    chart.timeScale().fitContent();

    // Crosshair hover listener for dynamic HUD
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData) {
        setHoveredCandle(null);
        return;
      }
      const timeStr = typeof param.time === 'string' ? param.time : '';
      const match = candleData.candles.find((c) => c.time === timeStr);
      if (match) {
        setHoveredCandle(match);
      }
    });

    // ResizeObserver for dynamic responsiveness
    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries || entries.length === 0 || !chartInstanceRef.current) return;
      const { width: newW, height: newH } = entries[0].contentRect;
      if (newW > 0 && newH > 0) {
        chartInstanceRef.current.applyOptions({ width: newW, height: newH });
      }
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [isOpen, candleData, chartStyle, showEma20, showEma50]);

  if (!isOpen || !stock) return null;

  const displayCandle = hoveredCandle || (candleData?.candles ? candleData.candles[candleData.candles.length - 1] : null);
  const summary = candleData?.summary;
  const changePct = summary ? summary.change_pct : (stock.return_since_listing_pct ?? 0);
  const isPositive = changePct >= 0;

  // Day change calculation for hovered candle
  let hoveredChangePct: number | null = null;
  if (displayCandle && displayCandle.open > 0) {
    hoveredChangePct = ((displayCandle.close - displayCandle.open) / displayCandle.open) * 100;
  }

  return (
    <div
      className={`fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center animate-fade-in ${
        isMaximized ? 'p-0' : 'p-2 sm:p-4 md:p-6'
      }`}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isMaximized) onClose();
      }}
    >
      <div
        className={`relative bg-navy-900 border border-navy-700/80 shadow-2xl flex flex-col overflow-hidden text-gray-200 transition-all duration-150 ${
          isMaximized
            ? 'w-full h-full rounded-none border-0'
            : 'w-full max-w-6xl h-[92vh] sm:h-[88vh] rounded-2xl'
        }`}
      >
        
        {/* Top Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-3 bg-navy-950/90 border-b border-navy-800">
          
          {/* Stock Info & Exchange Switcher */}
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xl sm:text-2xl font-black tracking-wider text-white font-mono">
                  {stock.symbol}
                </span>

                {/* Exchange Switcher */}
                <div className="flex items-center bg-navy-800 border border-navy-700 rounded-lg p-0.5 text-[11px] font-bold">
                  <button
                    onClick={() => setExchange('NSE')}
                    className={`px-2 py-0.5 rounded transition ${
                      exchange === 'NSE'
                        ? 'bg-electric-500 text-white shadow-sm'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    NSE
                  </button>
                  <button
                    onClick={() => setExchange('BSE')}
                    className={`px-2 py-0.5 rounded transition ${
                      exchange === 'BSE'
                        ? 'bg-electric-500 text-white shadow-sm'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    BSE
                  </button>
                </div>

                {stock.category && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-navy-800 text-blue-300 border border-navy-700">
                    {stock.category}
                  </span>
                )}

                {stock.is_relisted !== undefined && (
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                      stock.is_relisted
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                    }`}
                  >
                    {stock.is_relisted ? 'Re-listed' : 'Fresh IPO'}
                  </span>
                )}
              </div>

              {stock.company_name && (
                <p className="text-xs text-gray-400 truncate max-w-xs sm:max-w-md">
                  {stock.company_name}
                </p>
              )}
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-3 sm:gap-4 flex-wrap text-xs">
            {summary && (
              <div className="text-right">
                <span className="text-[10px] text-gray-400 block uppercase">LTP / CMP</span>
                <span className="font-mono font-bold text-white text-sm sm:text-base">
                  ₹{summary.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            )}

            {summary && (
              <div className="text-right">
                <span className="text-[10px] text-gray-400 block uppercase">1D Change</span>
                <span
                  className={`font-mono font-bold text-xs sm:text-sm px-1.5 py-0.5 rounded ${
                    isPositive
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-coral-500/20 text-coral-400'
                  }`}
                >
                  {isPositive ? '+' : ''}
                  {summary.change_pct.toFixed(2)}%
                </span>
              </div>
            )}

            {stock.operating_profit_growth_pct !== undefined && stock.operating_profit_growth_pct !== null && (
              <div className="text-right hidden md:block">
                <span className="text-[10px] text-gray-400 block uppercase">Op. Profit YoY</span>
                <span
                  className={`font-mono font-semibold text-xs px-1.5 py-0.5 rounded ${
                    stock.operating_profit_growth_pct > 0
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {stock.operating_profit_growth_pct > 0 ? '▲ +' : '▼ '}
                  {stock.operating_profit_growth_pct.toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Controls: Candle Interval (Daily/Weekly/Monthly), Period, Chart Style, EMAs, Maximize, Close */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Candle Interval (Daily/Weekly/Monthly) - Daily Default */}
            <div className="flex items-center bg-navy-800 border border-navy-700 rounded-lg p-0.5 text-xs font-semibold">
              <button
                onClick={() => setCandleInterval('1d')}
                className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                  candleInterval === '1d'
                    ? 'bg-electric-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Daily Candles (Default)"
              >
                <span>1D</span>
                <span className="hidden sm:inline text-[10px] opacity-85">Daily</span>
              </button>
              <button
                onClick={() => setCandleInterval('1wk')}
                className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                  candleInterval === '1wk'
                    ? 'bg-electric-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Weekly Candles"
              >
                <span>1W</span>
                <span className="hidden sm:inline text-[10px] opacity-85">Weekly</span>
              </button>
              <button
                onClick={() => setCandleInterval('1mo')}
                className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                  candleInterval === '1mo'
                    ? 'bg-electric-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Monthly Candles"
              >
                <span>1M</span>
                <span className="hidden sm:inline text-[10px] opacity-85">Monthly</span>
              </button>
            </div>

            {/* Timeframe range selector */}
            <div className="flex items-center bg-navy-800 border border-navy-700 rounded-lg p-0.5 text-xs font-mono">
              {(['1mo', '3mo', '6mo', '1y', 'max'] as Period[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2 py-0.5 rounded transition ${
                    period === p
                      ? 'bg-navy-700 text-electric-400 font-bold border border-navy-600'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {p === '1mo' ? '1M' : p === '3mo' ? '3M' : p === '6mo' ? '6M' : p === '1y' ? '1Y' : 'ALL'}
                </button>
              ))}
            </div>

            {/* Chart Style Switcher */}
            <div className="flex items-center bg-navy-800 border border-navy-700 rounded-lg p-0.5 text-xs font-semibold">
              <button
                onClick={() => setChartStyle('candles')}
                className={`px-2 py-0.5 rounded transition ${
                  chartStyle === 'candles'
                    ? 'bg-navy-700 text-emerald-400'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Candlestick chart"
              >
                🕯️
              </button>
              <button
                onClick={() => setChartStyle('area')}
                className={`px-2 py-0.5 rounded transition ${
                  chartStyle === 'area'
                    ? 'bg-navy-700 text-emerald-400'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Area Line chart"
              >
                📈
              </button>
            </div>

            {/* EMA Toggles */}
            <div className="hidden sm:flex items-center gap-1">
              <button
                onClick={() => setShowEma20(!showEma20)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono border transition ${
                  showEma20
                    ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                    : 'bg-navy-800 text-gray-500 border-navy-700'
                }`}
              >
                20 EMA
              </button>
              <button
                onClick={() => setShowEma50(!showEma50)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono border transition ${
                  showEma50
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    : 'bg-navy-800 text-gray-500 border-navy-700'
                }`}
              >
                50 EMA
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => {
                if (!stock) return;
                setLoading(true);
                stocksAPI.getCandles(stock.symbol, { exchange, period, interval: candleInterval, refresh: true })
                  .then(setCandleData)
                  .finally(() => setLoading(false));
              }}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-navy-800 rounded-lg transition"
              title="Force reload latest price data"
            >
              <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>

            {/* Maximize / Minimize Button */}
            <button
              onClick={() => setIsMaximized(!isMaximized)}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-navy-800 rounded-lg transition"
              title={isMaximized ? "Restore window (F / Esc)" : "Maximize to full screen (F)"}
            >
              {isMaximized ? (
                /* Restore icon (two overlapping windows) */
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5M15 15l5.25 5.25" />
                </svg>
              ) : (
                /* Maximize icon (expand outward arrows) */
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                </svg>
              )}
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-navy-800 rounded-lg transition"
              title="Close (Esc)"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Dynamic Crosshair / Candle Stats Strip (HUD) */}
        {displayCandle && (
          <div className="px-4 sm:px-6 py-1.5 bg-navy-950/70 border-b border-navy-800/60 flex items-center justify-between flex-wrap gap-2 text-[11px] font-mono text-gray-400">
            <div className="flex items-center gap-3 sm:gap-4 flex-wrap">
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-navy-800 text-electric-300 border border-navy-700 uppercase">
                {candleInterval === '1d' ? 'Daily' : candleInterval === '1wk' ? 'Weekly' : 'Monthly'}
              </span>
              <span className="text-gray-300 font-semibold">{displayCandle.time}</span>
              <span>O: <span className="text-white font-bold">₹{displayCandle.open.toFixed(2)}</span></span>
              <span>H: <span className="text-emerald-400 font-bold">₹{displayCandle.high.toFixed(2)}</span></span>
              <span>L: <span className="text-coral-400 font-bold">₹{displayCandle.low.toFixed(2)}</span></span>
              <span>C: <span className={`font-bold ${displayCandle.close >= displayCandle.open ? 'text-emerald-400' : 'text-coral-400'}`}>₹{displayCandle.close.toFixed(2)}</span></span>
              {hoveredChangePct !== null && (
                <span className={hoveredChangePct >= 0 ? 'text-emerald-400 font-bold' : 'text-coral-400 font-bold'}>
                  ({hoveredChangePct >= 0 ? '+' : ''}{hoveredChangePct.toFixed(2)}%)
                </span>
              )}
              <span>Vol: <span className="text-white">{displayCandle.volume.toLocaleString('en-IN')}</span></span>
            </div>
            <div className="flex items-center gap-3">
              {displayCandle.ema20 && showEma20 && (
                <span className="text-sky-300">20 EMA: ₹{displayCandle.ema20.toFixed(2)}</span>
              )}
              {displayCandle.ema50 && showEma50 && (
                <span className="text-purple-300">50 EMA: ₹{displayCandle.ema50.toFixed(2)}</span>
              )}
              {displayCandle.rsi !== null && displayCandle.rsi !== undefined && (
                <span className={`font-semibold ${displayCandle.rsi >= 70 ? 'text-amber-400' : displayCandle.rsi <= 30 ? 'text-emerald-400' : 'text-gray-300'}`}>
                  RSI(14): {displayCandle.rsi.toFixed(1)}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Main Chart Canvas Area */}
        <div className="flex-1 w-full h-full relative bg-[#0a0f1d] overflow-hidden">
          {/* Loading Spinner */}
          {loading && !candleData && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-navy-950/80 gap-3">
              <div className="w-10 h-10 border-3 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
              <p className="text-xs text-gray-400 font-medium">Downloading accurate NSE prices for {stock.symbol}...</p>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center">
              <div className="text-3xl mb-2">⚠️</div>
              <p className="text-sm text-coral-400 font-semibold mb-1">Failed to load price data</p>
              <p className="text-xs text-gray-400 max-w-md mb-4">{error}</p>
              <button
                onClick={() => {
                  setLoading(true);
                  stocksAPI.getCandles(stock.symbol, { exchange, period, refresh: true })
                    .then(setCandleData)
                    .finally(() => setLoading(false));
                }}
                className="px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-white text-xs font-semibold border border-navy-700 transition"
              >
                Retry Download
              </button>
            </div>
          )}

          {/* Lightweight Chart Container */}
          <div ref={chartContainerRef} className="w-full h-full" />
        </div>

        {/* Bottom Information Footer */}
        <div className="px-4 py-2 bg-navy-950/90 border-t border-navy-800 flex items-center justify-between text-[11px] text-gray-500 flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Accurate NSE Prices ({summary?.ticker_used || `${exchange}:${stock.symbol}`})</span>
            </span>
            <span>•</span>
            <span className="text-gray-300 font-medium">
              Timeframe: <span className="text-electric-400 font-bold">{candleInterval === '1d' ? '1D (Daily)' : candleInterval === '1wk' ? '1W (Weekly)' : '1M (Monthly)'}</span>
            </span>
            {summary && (
              <>
                <span>•</span>
                <span>Range: ₹{summary.low_period.toFixed(2)} – ₹{summary.high_period.toFixed(2)}</span>
                <span>•</span>
                <span>{summary.candle_count} Candles</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3 text-gray-400">
            {isMaximized && (
              <>
                <span className="text-electric-400 font-bold">Fullscreen Active</span>
                <span>•</span>
              </>
            )}
            <span>Clean In-App Canvas</span>
            <span>•</span>
            <span>Press Esc to close (or F to toggle fullscreen)</span>
          </div>
        </div>

      </div>
    </div>
  );
}
