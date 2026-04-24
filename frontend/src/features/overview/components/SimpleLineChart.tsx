import type { OverviewChartPoint } from '../types';

type SimpleLineChartProps = {
  title: string;
  subtitle: string;
  points: OverviewChartPoint[];
};

export function SimpleLineChart({ title, subtitle, points }: SimpleLineChartProps) {
  const width = 640;
  const height = 240;
  const paddingX = 44;
  const paddingY = 32;

  const maxValue = Math.max(...points.map((point) => point.value), 1);
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  const coordinates = points.map((point, index) => {
    const x =
      points.length === 1
        ? width / 2
        : paddingX + (index / (points.length - 1)) * chartWidth;

    const y = paddingY + chartHeight - (point.value / maxValue) * chartHeight;

    return {
      ...point,
      x,
      y,
    };
  });

  const polylinePoints = coordinates.map((point) => `${point.x},${point.y}`).join(' ');

  return (
    <section className="card overview-chart-card">
      <div className="card-header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>

      <div className="overview-chart">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          <line
            x1={paddingX}
            y1={height - paddingY}
            x2={width - paddingX}
            y2={height - paddingY}
            className="overview-chart__axis"
          />

          <line
            x1={paddingX}
            y1={paddingY}
            x2={paddingX}
            y2={height - paddingY}
            className="overview-chart__axis"
          />

          {[0.25, 0.5, 0.75, 1].map((step) => {
            const y = paddingY + chartHeight - step * chartHeight;

            return (
              <line
                key={step}
                x1={paddingX}
                y1={y}
                x2={width - paddingX}
                y2={y}
                className="overview-chart__grid"
              />
            );
          })}

          <polyline
            points={polylinePoints}
            fill="none"
            className="overview-chart__line"
          />

          {coordinates.map((point) => (
            <g key={point.label}>
              <circle
                cx={point.x}
                cy={point.y}
                r="5"
                className="overview-chart__dot"
              />

              <text
                x={point.x}
                y={height - 8}
                textAnchor="middle"
                className="overview-chart__label"
              >
                {point.label}
              </text>

              <text
                x={point.x}
                y={point.y - 12}
                textAnchor="middle"
                className="overview-chart__value"
              >
                {point.value}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </section>
  );
}