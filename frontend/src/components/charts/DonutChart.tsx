import { useEffect, useRef } from 'react';

interface DonutChartProps {
  segments: { label: string; value: number; color: string }[];
  centerLabel?: string;
  centerValue?: string;
  size?: number;
}

export default function DonutChart({ segments, centerLabel, centerValue, size = 220 }: DonutChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const radius = size / 2 - 20;
    const innerRadius = radius * 0.65;
    const total = segments.reduce((sum, s) => sum + s.value, 0);

    let startAngle = -Math.PI / 2;

    // Animated draw
    const animate = (progress: number) => {
      ctx.clearRect(0, 0, size, size);

      // Draw segments
      let currentStart = -Math.PI / 2;
      segments.forEach((segment) => {
        const sweepAngle = (segment.value / total) * Math.PI * 2 * progress;
        const endAngle = currentStart + sweepAngle;

        ctx.beginPath();
        ctx.arc(cx, cy, radius, currentStart, endAngle);
        ctx.arc(cx, cy, innerRadius, endAngle, currentStart, true);
        ctx.closePath();

        ctx.fillStyle = segment.color;
        ctx.fill();

        // Subtle shadow
        ctx.shadowColor = segment.color;
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;

        currentStart = endAngle;
      });

      // Inner circle (dark)
      ctx.beginPath();
      ctx.arc(cx, cy, innerRadius - 2, 0, Math.PI * 2);
      ctx.fillStyle = '#0a0e27';
      ctx.fill();

      // Center text
      if (centerValue) {
        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 22px Inter, sans-serif';
        ctx.fillText(centerValue, cx, cy + (centerLabel ? -4 : 6));
      }
      if (centerLabel) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText(centerLabel, cx, cy + 16);
      }
    };

    // Animation loop
    let frame = 0;
    const totalFrames = 40;
    const step = () => {
      frame++;
      const progress = Math.min(frame / totalFrames, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Ease out cubic
      animate(eased);
      if (frame < totalFrames) {
        requestAnimationFrame(step);
      }
    };
    step();
  }, [segments, centerLabel, centerValue, size]);

  return (
    <div className="flex flex-col items-center gap-4">
      <canvas
        ref={canvasRef}
        style={{ width: size, height: size }}
        className="drop-shadow-lg"
      />
      <div className="flex flex-wrap gap-4 justify-center">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-xs text-gray-400">{s.label}</span>
            <span className="text-xs font-mono text-gray-300">
              ₹{(s.value / 100000).toFixed(1)}L
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
