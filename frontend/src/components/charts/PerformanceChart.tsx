import { useEffect, useRef } from 'react';
import type { PerformancePoint } from '../../api/client';

interface PerformanceChartProps {
  data: PerformancePoint[];
  portfolioReturn: number;
  niftyReturn: number;
  midcapReturn: number;
}

export default function PerformanceChart({
  data,
  portfolioReturn,
  niftyReturn,
  midcapReturn,
}: PerformanceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.length) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const padding = { top: 20, right: 20, bottom: 30, left: 60 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Normalize to percentage returns
    const basePortfolio = data[0].portfolio_value;
    const baseNifty = data[0].nifty_50_value;
    const baseMidcap = data[0].nifty_midcap_150_value;

    const portfolioReturns = data.map((d) => ((d.portfolio_value / basePortfolio) - 1) * 100);
    const niftyReturns = data.map((d) => ((d.nifty_50_value / baseNifty) - 1) * 100);
    const midcapReturns = data.map((d) => ((d.nifty_midcap_150_value / baseMidcap) - 1) * 100);

    const allValues = [...portfolioReturns, ...niftyReturns, ...midcapReturns];
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const range = maxVal - minVal || 1;
    const padded = range * 0.1;

    const xScale = (i: number) => padding.left + (i / (data.length - 1)) * chartW;
    const yScale = (v: number) =>
      padding.top + chartH - ((v - (minVal - padded)) / (range + padded * 2)) * chartH;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Grid lines
    ctx.strokeStyle = 'rgba(30, 39, 92, 0.5)';
    ctx.lineWidth = 1;
    const gridCount = 5;
    for (let i = 0; i <= gridCount; i++) {
      const y = padding.top + (i / gridCount) * chartH;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      // Y-axis labels
      const val = maxVal + padded - ((i / gridCount) * (range + padded * 2));
      ctx.fillStyle = '#6b7280';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${val.toFixed(1)}%`, padding.left - 8, y + 4);
    }

    // Zero line
    const zeroY = yScale(0);
    ctx.strokeStyle = 'rgba(107, 114, 128, 0.3)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding.left, zeroY);
    ctx.lineTo(width - padding.right, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw line function
    const drawLine = (values: number[], color: string, lineWidth: number, gradient?: boolean) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.beginPath();
      values.forEach((v, i) => {
        const x = xScale(i);
        const y = yScale(v);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Gradient fill
      if (gradient) {
        const grad = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
        grad.addColorStop(0, color.replace(')', ', 0.15)').replace('rgb', 'rgba'));
        grad.addColorStop(1, color.replace(')', ', 0.0)').replace('rgb', 'rgba'));
        ctx.lineTo(xScale(values.length - 1), padding.top + chartH);
        ctx.lineTo(xScale(0), padding.top + chartH);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
      }
    };

    // Draw lines
    drawLine(midcapReturns, 'rgb(251, 191, 36)', 1.5);
    drawLine(niftyReturns, 'rgb(107, 114, 128)', 1.5);
    drawLine(portfolioReturns, 'rgb(79, 108, 247)', 2.5, true);

    // End dots
    const lastIdx = data.length - 1;
    [
      { values: portfolioReturns, color: '#4f6cf7' },
      { values: niftyReturns, color: '#6b7280' },
      { values: midcapReturns, color: '#fbbf24' },
    ].forEach(({ values, color }) => {
      ctx.beginPath();
      ctx.arc(xScale(lastIdx), yScale(values[lastIdx]), 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#0a0e27';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // X-axis labels (first, mid, last)
    ctx.fillStyle = '#6b7280';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    [0, Math.floor(data.length / 2), lastIdx].forEach((i) => {
      const d = new Date(data[i].date);
      ctx.fillText(
        d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
        xScale(i),
        height - 8
      );
    });
  }, [data]);

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        className="w-full h-64"
        style={{ height: 256 }}
      />
      <div ref={tooltipRef} />

      {/* Legend */}
      <div className="flex items-center gap-6 mt-3 justify-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-electric-500 rounded" />
          <span className="text-xs text-gray-400">Portfolio</span>
          <span className={`text-xs font-mono font-semibold ${portfolioReturn >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
            {portfolioReturn >= 0 ? '+' : ''}{portfolioReturn.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-gray-500 rounded" />
          <span className="text-xs text-gray-400">Nifty 50</span>
          <span className={`text-xs font-mono font-semibold ${niftyReturn >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
            {niftyReturn >= 0 ? '+' : ''}{niftyReturn.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-amber-400 rounded" />
          <span className="text-xs text-gray-400">Midcap 150</span>
          <span className={`text-xs font-mono font-semibold ${midcapReturn >= 0 ? 'text-emerald-400' : 'text-coral-400'}`}>
            {midcapReturn >= 0 ? '+' : ''}{midcapReturn.toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
