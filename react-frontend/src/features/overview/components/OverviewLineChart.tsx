import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type OverviewLineChartProps<TData extends Record<string, string | number>> = {
  title: string;
  subtitle: string;
  data: TData[];
  countDataKey: keyof TData;
  countLabel: string;
  priceDataKey: keyof TData;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function OverviewLineChart<TData extends Record<string, string | number>>({
  title,
  subtitle,
  data,
  countDataKey,
  countLabel,
  priceDataKey,
}: OverviewLineChartProps<TData>) {
  return (
    <section className="rounded-2xl border border-mph-border bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-mph-text">{title}</h2>
        <p className="mt-1 text-sm text-mph-muted">{subtitle}</p>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{
              top: 12,
              right: 20,
              left: 10,
              bottom: 8,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#dee2e6" />

            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={{ stroke: '#dee2e6' }}
              tick={{ fill: '#6c757d', fontSize: 12 }}
            />

            <YAxis
              yAxisId="count"
              allowDecimals={false}
              tickLine={false}
              axisLine={{ stroke: '#dee2e6' }}
              tick={{ fill: '#6c757d', fontSize: 12 }}
            />

            <YAxis
              yAxisId="price"
              orientation="right"
              tickFormatter={(value) => formatCurrency(Number(value))}
              tickLine={false}
              axisLine={{ stroke: '#dee2e6' }}
              tick={{ fill: '#6c757d', fontSize: 12 }}
            />

            <Tooltip
              formatter={(value, name) => {
                if (name === 'Average Sales Price') {
                  return [formatCurrency(Number(value)), name];
                }

                return [Number(value).toLocaleString(), name];
              }}
              labelClassName="font-semibold text-[#212529]"
              contentStyle={{
                borderRadius: '0.75rem',
                borderColor: '#dee2e6',
                color: '#212529',
                boxShadow:
                  '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
              }}
            />

            <Legend />

            <Line
              yAxisId="count"
              type="monotone"
              dataKey={countDataKey as string}
              name={countLabel}
              stroke="#0f766e"
              strokeWidth={3}
              dot={{
                r: 4,
                fill: '#ffffff',
                stroke: '#0f766e',
                strokeWidth: 2,
              }}
              activeDot={{
                r: 6,
                fill: '#0f766e',
                stroke: '#ffffff',
                strokeWidth: 2,
              }}
            />

            <Line
              yAxisId="price"
              type="monotone"
              dataKey={priceDataKey as string}
              name="Average Sales Price"
              stroke="#343a40"
              strokeWidth={3}
              strokeDasharray="6 4"
              dot={{
                r: 4,
                fill: '#ffffff',
                stroke: '#343a40',
                strokeWidth: 2,
              }}
              activeDot={{
                r: 6,
                fill: '#343a40',
                stroke: '#ffffff',
                strokeWidth: 2,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}