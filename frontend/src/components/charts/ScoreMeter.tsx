interface ScoreMeterProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export default function ScoreMeter({ score, size = 64, strokeWidth = 5 }: ScoreMeterProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  // Color based on score
  let color = '#f43f5e'; // < 50
  if (score >= 75) color = '#10b981';
  else if (score >= 60) color = '#4f6cf7';
  else if (score >= 50) color = '#fbbf24';

  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(30, 39, 92, 0.5)"
          strokeWidth={strokeWidth}
        />
        {/* Score ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
          style={{
            filter: `drop-shadow(0 0 6px ${color}40)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          className="text-sm font-bold font-mono"
          style={{ color }}
        >
          {Math.round(score)}
        </span>
      </div>
    </div>
  );
}
