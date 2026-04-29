import { useLeadsQuery } from '@features/leads/api/queries';
import { CreateLeadDrawer } from '@features/leads/components/CreateLeadDrawer';
import { LeadsTable } from '@features/leads/components/LeadsTable';
import {
    isActiveLeadStatus,
    leadSources,
    leadStatuses,
    type LeadSource,
    type LeadStatus,
} from '@features/leads/schema';
import { useState, type SubmitEventHandler } from 'react';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function LeadsListPage() {
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<LeadStatus | ''>('');
  const [source, setSource] = useState<LeadSource | ''>('');

  const leadsQuery = useLeadsQuery({
    search,
    status,
    source,
  });

  const leads = leadsQuery.data?.results ?? [];

  const activeLeads = leads.filter((lead) => isActiveLeadStatus(lead.status));
  const estimatedPipeline = activeLeads.reduce(
    (total, lead) => total + lead.estimatedSalesPrice,
    0,
  );

  const handleSearch: SubmitEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    setSearch(searchInput);
  };

  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-mph-primary">CRM</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Leads</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track early-stage opportunities before they become quotes.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setCreateDrawerOpen(true)}
          className="inline-flex rounded-lg bg-mph-primary px-4 py-2 text-sm font-semibold text-white hover:bg-mph-primary-hover"
        >
          New Lead
        </button>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Total Leads</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {leadsQuery.data?.count ?? 0}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Active Leads</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {activeLeads.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Qualified</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {leads.filter((lead) => lead.status === 'Qualified').length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Est. Pipeline</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {formatCurrency(estimatedPipeline)}
          </p>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <form
          onSubmit={handleSearch}
          className="grid gap-3 lg:grid-cols-[1fr_220px_220px_auto]"
        >
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search company, opportunity, lead number, market, or owner"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
          />

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as LeadStatus | '')}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
          >
            <option value="">All statuses</option>
            {leadStatuses.map((leadStatus) => (
              <option key={leadStatus} value={leadStatus}>
                {leadStatus}
              </option>
            ))}
          </select>

          <select
            value={source}
            onChange={(event) => setSource(event.target.value as LeadSource | '')}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
          >
            <option value="">All sources</option>
            {leadSources.map((leadSource) => (
              <option key={leadSource} value={leadSource}>
                {leadSource}
              </option>
            ))}
          </select>

          <button
            type="submit"
            className="rounded-lg bg-[#343a40] px-4 py-2 text-sm font-semibold text-white hover:bg-[#495057]"
          >
            Search
          </button>
        </form>
      </section>

      {leadsQuery.isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          Loading leads...
        </div>
      ) : null}

      {leadsQuery.isError ? (
        <div className="rounded-2xl border border-red-200 bg-white p-6 text-sm text-red-700 shadow-sm">
          Unable to load leads.
        </div>
      ) : null}

      {!leadsQuery.isLoading && !leadsQuery.isError && leads.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          No leads match your filters.
        </div>
      ) : null}

      {!leadsQuery.isLoading && !leadsQuery.isError && leads.length > 0 ? (
        <LeadsTable leads={leads} />
      ) : null}

      <CreateLeadDrawer
        open={createDrawerOpen}
        onClose={() => setCreateDrawerOpen(false)}
      />
    </div>
  );
}