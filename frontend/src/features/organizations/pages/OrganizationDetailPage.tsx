import { Link, useParams } from 'react-router-dom';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { PageHeader } from '@/components/ui/PageHeader';
import { useOrganizationDetailQuery } from '@/features/organizations/api/queries';
import { useTenant } from '@/features/tenant/TenantContext';
import { ApiError } from '@/lib/utils/http';

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatMoney(value: number | null) {
  if (value == null) return '—';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function OrganizationDetailPage() {
  const { organizationId = '' } = useParams<{ organizationId: string }>();
  const { organization: tenantOrganization, capabilities } = useTenant();
  const organizationQuery = useOrganizationDetailQuery(organizationId);

  if (organizationQuery.isPending) {
    return <LoadingScreen message="Loading organization details…" />;
  }

  const errorPayload = organizationQuery.error instanceof ApiError ? organizationQuery.error.payload : null;

  if (organizationQuery.isError || !organizationQuery.data) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow={tenantOrganization?.slug ? `${tenantOrganization.slug}.mypipelinehero.com` : undefined}
          title="Organization details"
          description="The requested organization could not be loaded from the mocked endpoint."
          actions={
            <Link className="ui-button ui-button--secondary" to="/organizations">
              Back to organizations
            </Link>
          }
        />

        <Card>
          <h3>Could not load organization</h3>
          <p>
            This state is ready for a real backend later. A missing ID should return a 404 and an unavailable endpoint should return a 5xx response.
          </p>
          {errorPayload && typeof errorPayload === 'object' ? (
            <pre className="ui-error-block">{JSON.stringify(errorPayload, null, 2)}</pre>
          ) : null}
        </Card>
      </div>
    );
  }

  const detailOrganization = organizationQuery.data;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={tenantOrganization?.slug ? `${tenantOrganization.slug}.mypipelinehero.com` : undefined}
        title={detailOrganization.name}
        description="A contract-first organization details page wired to its own route and mock handler so the list-to-detail flow works before Django is finished."
        actions={
          <div className="ui-inline-actions">
            <Link className="ui-button ui-button--secondary" to="/organizations">
              Back to organizations
            </Link>
            <Button disabled={!capabilities.includes('clients.edit')}>Edit organization</Button>
          </div>
        }
      />

      <div className="page-grid page-grid--three-up">
        <Card>
          <p className="stat-card__label">Status</p>
          <strong className="stat-card__value organization-stat__status">
            <Badge tone={detailOrganization.status === 'active' ? 'success' : 'neutral'}>{detailOrganization.status}</Badge>
          </strong>
          <span className="stat-card__hint">Lifecycle stage: {detailOrganization.lifecycle_stage}</span>
        </Card>
        <Card>
          <p className="stat-card__label">Annual revenue</p>
          <strong className="stat-card__value">{formatMoney(detailOrganization.annual_revenue)}</strong>
          <span className="stat-card__hint">Employees: {detailOrganization.employee_count ?? '—'}</span>
        </Card>
        <Card>
          <p className="stat-card__label">Last updated</p>
          <strong className="stat-card__value organization-stat__date">{formatDateTime(detailOrganization.updated_at)}</strong>
          <span className="stat-card__hint">Created {formatDateTime(detailOrganization.created_at)}</span>
        </Card>
      </div>

      <div className="page-grid page-grid--detail">
        <Card>
          <div className="detail-section">
            <h2>Overview</h2>
            <dl className="detail-grid">
              <div>
                <dt>Industry</dt>
                <dd>{detailOrganization.industry ?? '—'}</dd>
              </div>
              <div>
                <dt>Owner</dt>
                <dd>{detailOrganization.owner_name ?? 'Unassigned'}</dd>
              </div>
              <div>
                <dt>Website</dt>
                <dd>
                  {detailOrganization.website ? (
                    <a href={detailOrganization.website} target="_blank" rel="noreferrer">
                      {detailOrganization.website}
                    </a>
                  ) : (
                    '—'
                  )}
                </dd>
              </div>
              <div>
                <dt>Main phone</dt>
                <dd>{detailOrganization.phone ?? '—'}</dd>
              </div>
            </dl>
          </div>
        </Card>

        <Card>
          <div className="detail-section">
            <h2>Primary contact</h2>
            <dl className="detail-grid">
              <div>
                <dt>Name</dt>
                <dd>{detailOrganization.primary_contact_name ?? '—'}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{detailOrganization.primary_contact_email ?? '—'}</dd>
              </div>
              <div>
                <dt>Billing address</dt>
                <dd>{detailOrganization.billing_address ?? '—'}</dd>
              </div>
              <div>
                <dt>Service address</dt>
                <dd>{detailOrganization.service_address ?? '—'}</dd>
              </div>
            </dl>
          </div>
        </Card>
      </div>

      <div className="page-grid page-grid--two-up">
        <Card>
          <div className="detail-section">
            <h2>Notes</h2>
            <p className="detail-copy">{detailOrganization.notes || 'No notes recorded for this organization yet.'}</p>
          </div>
        </Card>

        <Card>
          <div className="detail-section">
            <h2>Tags</h2>
            {detailOrganization.tags.length ? (
              <div className="detail-tags">
                {detailOrganization.tags.map((tag) => (
                  <Badge key={tag} tone="neutral">{tag}</Badge>
                ))}
              </div>
            ) : (
              <p className="detail-copy">No tags assigned.</p>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <div className="detail-section">
          <h2>Recent activity</h2>
          <div className="detail-activity-list">
            {detailOrganization.recent_activity.map((item) => (
              <div key={item.id} className="detail-activity-item">
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                </div>
                <span>{item.time_label}</span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
