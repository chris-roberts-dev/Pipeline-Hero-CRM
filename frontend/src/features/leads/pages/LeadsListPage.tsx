import { type SubmitEventHandler, useState } from 'react';
import { Link } from 'react-router-dom';
import { useLeadsQuery } from '../api/queries';
import { CreateLeadDrawer } from '../components/CreateLeadDrawer';
import type { LeadStatus } from '../types';

const statuses: Array<LeadStatus | ''> = [
  '',
  'New',
  'Contacted',
  'Qualified',
  'Unqualified',
  'Converted',
  'Archived',
];

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function getStatusClass(status: LeadStatus) {
  switch (status) {
    case 'New':
      return 'status-badge status-badge--info';
    case 'Contacted':
      return 'status-badge status-badge--primary';
    case 'Qualified':
      return 'status-badge status-badge--success';
    case 'Unqualified':
      return 'status-badge status-badge--warning';
    case 'Converted':
      return 'status-badge status-badge--dark';
    case 'Archived':
      return 'status-badge status-badge--muted';
    default:
      return 'status-badge';
  }
}

export function LeadsListPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<LeadStatus | ''>('');
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);

  const leadsQuery = useLeadsQuery({ search, status });

 const handleSubmit: SubmitEventHandler<HTMLFormElement> = (event) => {
  event.preventDefault();
  setSearch(searchInput);
};

  const leads = leadsQuery.data?.results ?? [];

  return (
    <div className="page-stack">
      <div className="content-header">
        <div>
          <h1>Leads</h1>
          <p>Track early-stage opportunities before they become quotes.</p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={() => setCreateDrawerOpen(true)}
        >
          New Lead
        </button>
      </div>

      <div className="summary-grid">
        <div className="summary-card">
          <span>Total Leads</span>
          <strong>{leadsQuery.data?.count ?? 0}</strong>
        </div>

        <div className="summary-card">
          <span>Qualified</span>
          <strong>{leads.filter((lead) => lead.status === 'Qualified').length}</strong>
        </div>

        <div className="summary-card">
          <span>Estimated Pipeline</span>
          <strong>{formatCurrency(leads.reduce((sum, lead) => sum + lead.estimatedValue, 0))}</strong>
        </div>
      </div>

      <section className="card">
        <div className="card-header">
          <h2>Lead Pipeline</h2>
        </div>

        <form className="filter-bar" onSubmit={handleSubmit}>
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search company, opportunity, lead number, or owner"
          />

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as LeadStatus | '')}
          >
            {statuses.map((option) => (
              <option key={option || 'all'} value={option}>
                {option || 'All statuses'}
              </option>
            ))}
          </select>

          <button type="submit">Search</button>
        </form>

        {leadsQuery.isLoading && (
          <div className="empty-state">Loading leads...</div>
        )}

        {leadsQuery.isError && (
          <div className="empty-state empty-state--error">
            Unable to load leads.
          </div>
        )}

        {!leadsQuery.isLoading && !leadsQuery.isError && leads.length === 0 && (
          <div className="empty-state">No leads match your filters.</div>
        )}

        {!leadsQuery.isLoading && !leadsQuery.isError && leads.length > 0 && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Owner</th>
                  <th>Market</th>
                  <th>Estimated Value</th>
                  <th>Updated</th>
                </tr>
              </thead>

              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <Link to={`/leads/${lead.id}`} className="table-primary-link">
                        {lead.companyName}
                      </Link>
                      <div className="table-muted">
                        {lead.leadNumber} · {lead.opportunityName}
                      </div>
                    </td>
                    <td>
                      <span className={getStatusClass(lead.status)}>
                        {lead.status}
                      </span>
                    </td>
                    <td>{lead.source}</td>
                    <td>{lead.owner.name}</td>
                    <td>
                      {lead.market}
                      <div className="table-muted">{lead.location}</div>
                    </td>
                    <td>{formatCurrency(lead.estimatedValue)}</td>
                    <td>{new Date(lead.updatedAt).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <CreateLeadDrawer
        open={createDrawerOpen}
        onClose={() => setCreateDrawerOpen(false)}
      />
    </div>
  );
}