import { useMemo, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';

import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { PageHeader } from '@/components/ui/PageHeader';
import {
  useCompaniesQuery,
  type CompanyFilters,
} from '@/features/companies/api/queries';
import { CompaniesTable } from '@/features/companies/components/CompaniesTable';
import { useTenant } from '@/features/tenant/TenantContext';
import { ApiError } from '@/lib/utils/http';

function readFilters(searchParams: URLSearchParams): CompanyFilters {
  const page = Number(searchParams.get('page') ?? '1');
  const pageSize = Number(searchParams.get('page_size') ?? '10');
  const search = searchParams.get('search') ?? '';
  const statusParam = searchParams.get('status');
  const orderingParam = searchParams.get('ordering');

  return {
    page: Number.isFinite(page) && page > 0 ? page : 1,
    pageSize: Number.isFinite(pageSize) && pageSize > 0 ? pageSize : 10,
    search,
    status:
      statusParam === 'active' || statusParam === 'inactive' ? statusParam : 'all',
    ordering:
      orderingParam === 'updated_at' ||
      orderingParam === '-updated_at' ||
      orderingParam === 'name' ||
      orderingParam === '-name'
        ? orderingParam
        : '-updated_at',
  };
}

export function CompaniesListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { organization, capabilities } = useTenant();

  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const companiesQuery = useCompaniesQuery(filters);

  const companies = companiesQuery.data?.results ?? [];
  const total = companiesQuery.data?.count ?? 0;
  const currentPage = filters.page;
  const pageSize = filters.pageSize;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  function updateFilters(nextFilters: Partial<CompanyFilters>) {
    const merged = { ...filters, ...nextFilters };
    const nextParams = new URLSearchParams();

    if (merged.page > 1) {
      nextParams.set('page', String(merged.page));
    }
    if (merged.pageSize !== 10) {
      nextParams.set('page_size', String(merged.pageSize));
    }
    if (merged.search) {
      nextParams.set('search', merged.search);
    }
    if (merged.status !== 'all') {
      nextParams.set('status', merged.status);
    }
    if (merged.ordering !== '-updated_at') {
      nextParams.set('ordering', merged.ordering);
    }

    setSearchParams(nextParams, { replace: true });
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    updateFilters({
      page: 1,
      search: String(formData.get('search') ?? ''),
      status: (String(formData.get('status') ?? 'all') as CompanyFilters['status']) || 'all',
      ordering:
        (String(formData.get('ordering') ?? '-updated_at') as CompanyFilters['ordering']) ||
        '-updated_at',
    });
  }

  if (companiesQuery.isPending) {
    return <LoadingScreen message="Loading companies…" />;
  }

  const errorPayload = companiesQuery.error instanceof ApiError ? companiesQuery.error.payload : null;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={organization?.slug ? `${organization.slug}.mypipelinehero.com` : undefined}
        title="Companies"
        description="Contract-first first slice for the CRM frontend. The page is intentionally useful with no backend by relying on the local OpenAPI contract and MSW-backed endpoints."
        actions={<Button disabled={!capabilities.includes('clients.create')}>New company</Button>}
      />

      <div className="page-grid page-grid--three-up">
        <Card>
          <p className="stat-card__label">Visible records</p>
          <strong className="stat-card__value">{total}</strong>
          <span className="stat-card__hint">Scoped by tenant session and mocked RBAC rules</span>
        </Card>
        <Card>
          <p className="stat-card__label">Sort order</p>
          <strong className="stat-card__value">{filters.ordering}</strong>
          <span className="stat-card__hint">Driven from query params so list behavior stays backend-compatible</span>
        </Card>
        <Card>
          <p className="stat-card__label">Granted capabilities</p>
          <strong className="stat-card__value">{capabilities.length}</strong>
          <span className="stat-card__hint">UI can hide actions early, but the backend remains authoritative later</span>
        </Card>
      </div>

      <Card>
        <form className="companies-filters" onSubmit={handleSearchSubmit}>
          <label>
            <span>Search companies</span>
            <input name="search" type="search" defaultValue={filters.search} placeholder="Acme, Bluebird, Cedar…" />
          </label>

          <label>
            <span>Status</span>
            <select name="status" defaultValue={filters.status}>
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>

          <label>
            <span>Sort by</span>
            <select name="ordering" defaultValue={filters.ordering}>
              <option value="-updated_at">Recently updated</option>
              <option value="updated_at">Oldest updated</option>
              <option value="name">Name A–Z</option>
              <option value="-name">Name Z–A</option>
            </select>
          </label>

          <div className="companies-filters__actions">
            <Button type="submit">Apply filters</Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                updateFilters({ page: 1, pageSize: 10, search: '', status: 'all', ordering: '-updated_at' })
              }
            >
              Reset
            </Button>
          </div>
        </form>
      </Card>

      {companiesQuery.isError ? (
        <Card>
          <h3>Could not load companies</h3>
          <p>
            This state is also intentionally mockable. Use the <strong>Companies error</strong> scenario to design the page before the real Django endpoint exists.
          </p>
          {errorPayload && typeof errorPayload === 'object' ? (
            <pre className="ui-error-block">{JSON.stringify(errorPayload, null, 2)}</pre>
          ) : null}
        </Card>
      ) : (
        <>
          <Card>
            <CompaniesTable companies={companies} />
          </Card>

          <div className="companies-pagination">
            <span>
              Page <strong>{currentPage}</strong> of <strong>{pageCount}</strong>
            </span>
            <div className="companies-pagination__actions">
              <Button
                type="button"
                variant="secondary"
                disabled={currentPage <= 1}
                onClick={() => updateFilters({ page: currentPage - 1 })}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={currentPage >= pageCount}
                onClick={() => updateFilters({ page: currentPage + 1 })}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
