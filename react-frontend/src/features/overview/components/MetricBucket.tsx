import type { OverviewMetric } from '../schema';

type MetricBucketProps = {
  metric: OverviewMetric;
};

const bucketStyles: Record<OverviewMetric['key'], string> = {
  newLeads: 'bg-mph-primary',
  qualifiedLeads: 'bg-[#115e59]',
  contactedLeads: 'bg-[#3f6f76]',
  activeLeads: 'bg-mph-sidebar',
};

export function MetricBucket({ metric }: MetricBucketProps) {
  return (
    <article
      className={[
        'relative overflow-hidden rounded-2xl p-5 text-white shadow-sm',
        bucketStyles[metric.key],
      ].join(' ')}
    >
      <div className="relative z-10">
        <p className="text-sm font-medium text-white/85">{metric.label}</p>
        <p className="mt-3 text-3xl font-bold">{metric.value.toLocaleString()}</p>
        <p className="mt-2 text-sm text-white/80">{metric.helperText}</p>
      </div>

      <div className="absolute -bottom-8 -right-8 h-28 w-28 rounded-full bg-white/15" />
    </article>
  );
}