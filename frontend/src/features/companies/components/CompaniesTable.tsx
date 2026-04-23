import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import type { CompanySummary } from '@/features/companies/api/queries';

interface CompaniesTableProps {
  companies: CompanySummary[];
}

function formatDate(dateString: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(new Date(dateString));
}

export function CompaniesTable({ companies }: CompaniesTableProps) {
  if (!companies.length) {
    return (
      <EmptyState
        title="No companies found"
        description="This is a useful empty state for building the page before the real backend exists. Try another mock scenario or broaden the filters."
      />
    );
  }

  return (
    <div className="companies-table-wrap">
      <table className="companies-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Industry</th>
            <th>Owner</th>
            <th>Primary contact</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => (
            <tr key={company.id}>
              <td>
                <div className="companies-table__primary-cell">
                  <strong>{company.name}</strong>
                  <span>{company.primary_contact_email ?? 'No email on file'}</span>
                </div>
              </td>
              <td>
                <Badge tone={company.status === 'active' ? 'success' : 'neutral'}>
                  {company.status}
                </Badge>
              </td>
              <td>{company.industry ?? '—'}</td>
              <td>{company.owner_name ?? 'Unassigned'}</td>
              <td>{company.primary_contact_name ?? 'No primary contact'}</td>
              <td>{formatDate(company.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
