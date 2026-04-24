import { useOverviewQuery } from '../api/queries';
import { MetricBucket } from '../components/MetricBucket';
import { SimpleLineChart } from '../components/SimpleLineChart';

export function OverviewPage() {
  const overviewQuery = useOverviewQuery();

  if (overviewQuery.isLoading) {
    return <div className="empty-state">Loading overview...</div>;
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <div className="empty-state empty-state--error">
        Unable to load overview data.
      </div>
    );
  }

  const overview = overviewQuery.data;

  return (
    <div className="page-stack">
      <div className="content-header">
        <div>
          <h1>Overview</h1>
          <p>Platform activity, lead pipeline health, and organization growth.</p>
        </div>
      </div>

      <div className="overview-bucket-grid">
        {overview.metrics.map((metric) => (
          <MetricBucket key={metric.key} metric={metric} />
        ))}
      </div>

      <div className="overview-chart-grid">
        <SimpleLineChart
          title="Total Leads Over Time"
          subtitle="Monthly lead volume across the platform"
          points={overview.leadsOverTime}
        />

        <SimpleLineChart
          title="Total Organizations Over Time"
          subtitle="Monthly active organization growth"
          points={overview.organizationsOverTime}
        />
      </div>
    </div>
  );
}