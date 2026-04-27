import { useTenantOverviewQuery } from '../api/queries';
import { MetricBucket } from '../components/MetricBucket';
import { OverviewLineChart } from '../components/OverviewLineChart';

export function OverviewPage() {
  const overviewQuery = useTenantOverviewQuery();

  if (overviewQuery.isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-slate-900">Loading overview...</p>
        <p className="mt-1 text-sm text-slate-500">
          Fetching tenant pipeline metrics.
        </p>
      </div>
    );
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-red-700">
          Unable to load overview.
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Refresh the page or try again later.
        </p>
      </div>
    );
  }

  const overview = overviewQuery.data;

  return (
    <div className="grid gap-6">
      <div>
        <p className="text-sm font-medium text-mph-primary">Tenant overview</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Overview</h1>
        <p className="mt-1 text-sm text-slate-500">
          Lead activity, qualification progress, and average sales price trends.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {overview.metrics.map((metric) => (
          <MetricBucket key={metric.key} metric={metric} />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <OverviewLineChart
          title="Total Leads Over Time"
          subtitle="Total tenant leads with average sales price trend"
          data={overview.totalLeadsOverTime}
          countDataKey="totalLeads"
          countLabel="Total Leads"
          priceDataKey="averageSalesPrice"
        />

        <OverviewLineChart
          title="Contacted Leads Over Time"
          subtitle="Contacted tenant leads with average sales price trend"
          data={overview.contactedLeadsOverTime}
          countDataKey="contactedLeads"
          countLabel="Contacted Leads"
          priceDataKey="averageSalesPrice"
        />
      </section>
    </div>
  );
}