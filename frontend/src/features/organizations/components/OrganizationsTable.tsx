import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import type { OrganizationSummary } from '@/features/organizations/api/queries';

interface OrganizationsTableProps {
  organizations: OrganizationSummary[];
}

function formatDate(dateString: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(new Date(dateString));
}

export function OrganizationsTable({ organizations }: OrganizationsTableProps) {
  if (!organizations.length) {
    return (
      <EmptyState
        title="No organizations found"
        description="This is a useful empty state for building the page before the real backend exists. Try another mock scenario or broaden the filters."
      />
    );
  }

  return (
    <div className="organizations-table-wrap">
      <table className="organizations-table">
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
          {organizations.map((organization) => (
            <tr key={organization.id}>
              <td>
                <div className="organizations-table__primary-cell">
                  <Link className="organizations-table__name-link" to={`/organizations/${organization.id}`}>
                    {organization.name}
                  </Link>
                  <span>{organization.primary_contact_email ?? 'No email on file'}</span>
                </div>
              </td>
              <td>
                <Badge tone={organization.status === 'active' ? 'success' : 'neutral'}>
                  {organization.status}
                </Badge>
              </td>
              <td>{organization.industry ?? '—'}</td>
              <td>{organization.owner_name ?? 'Unassigned'}</td>
              <td>{organization.primary_contact_name ?? 'No primary contact'}</td>
              <td>{formatDate(organization.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
