import type { OverviewMetric } from '../types';

type MetricBucketProps = {
  metric: OverviewMetric;
};

function getMetricClass(key: OverviewMetric['key']) {
  switch (key) {
    case 'activeOrganizations':
      return 'overview-bucket overview-bucket--primary';
    case 'newLeads':
      return 'overview-bucket overview-bucket--info';
    case 'qualifiedLeads':
      return 'overview-bucket overview-bucket--success';
    case 'contactedLeads':
      return 'overview-bucket overview-bucket--warning';
    default:
      return 'overview-bucket';
  }
}

export function MetricBucket({ metric }: MetricBucketProps) {
  return (
    <article className={getMetricClass(metric.key)}>
      <div>
        <span>{metric.label}</span>
        <strong>{metric.value.toLocaleString()}</strong>
        <p>{metric.helperText}</p>
      </div>
    </article>
  );
}