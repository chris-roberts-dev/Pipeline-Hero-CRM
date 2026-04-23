import { http, HttpResponse } from 'msw';

import {
  type OrganizationCreateRequest,
  type OrganizationListResponse,
  type OrganizationSummary,
} from '@/features/organizations/api/queries';
import { buildApiPath } from '@/lib/api/client';
import { getSessionFixture } from '@/mocks/data/sessionFixtures';
import { getOrganizationsFixture, getOrganizationDetailFixture } from '@/mocks/data/organizationFixtures';
import { readScenarioFromRequest, withMockDelay } from '@/mocks/utils';

const DEFAULT_PAGE_SIZE = 10;

function sortOrganizations(organizations: OrganizationSummary[], ordering: string | null) {
  const items = [...organizations];

  if (ordering === 'name' || ordering === '-name') {
    items.sort((a, b) => a.name.localeCompare(b.name));
    return ordering === '-name' ? items.reverse() : items;
  }

  items.sort((a, b) => a.updated_at.localeCompare(b.updated_at));
  return ordering === 'updated_at' ? items : items.reverse();
}

function paginate(organizations: OrganizationSummary[], page: number, pageSize: number, url: URL): OrganizationListResponse {
  const count = organizations.length;
  const start = (page - 1) * pageSize;
  const end = start + pageSize;
  const results = organizations.slice(start, end);

  function buildPageLink(nextPage: number) {
    const nextUrl = new URL(url.toString());
    nextUrl.searchParams.set('page', String(nextPage));
    nextUrl.searchParams.set('page_size', String(pageSize));
    return `${nextUrl.pathname}${nextUrl.search}`;
  }

  return {
    count,
    next: end < count ? buildPageLink(page + 1) : null,
    previous: page > 1 ? buildPageLink(page - 1) : null,
    results,
  };
}

function requireOrganizationViewPermission(scenario: ReturnType<typeof readScenarioFromRequest>) {
  const session = getSessionFixture(scenario);
  if (!session) {
    return HttpResponse.json(
      { code: 'AUTH_REQUIRED', message: 'Authentication required.' },
      { status: 401 },
    );
  }

  if (!session.capabilities.includes('clients.view')) {
    return HttpResponse.json(
      { code: 'FORBIDDEN', message: 'You do not have permission to view organizations.' },
      { status: 403 },
    );
  }

  return null;
}

export const organizationsHandlers = [
  http.get(buildApiPath('/organizations/'), async ({ request }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const denied = requireOrganizationViewPermission(scenario);
    if (denied) {
      return denied;
    }

    if (scenario === 'organizations-error') {
      return HttpResponse.json(
        { code: 'MOCK_FAILURE', message: 'Simulated organizations endpoint failure.' },
        { status: 500 },
      );
    }

    const url = new URL(request.url);
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);
    const pageSize = Math.max(1, Number(url.searchParams.get('page_size') ?? String(DEFAULT_PAGE_SIZE)) || DEFAULT_PAGE_SIZE);
    const search = (url.searchParams.get('search') ?? '').trim().toLowerCase();
    const status = url.searchParams.get('status');
    const ordering = url.searchParams.get('ordering');

    let organizations = getOrganizationsFixture(scenario);

    if (status === 'active' || status === 'inactive') {
      organizations = organizations.filter((organization) => organization.status === status);
    }

    if (search) {
      organizations = organizations.filter((organization) => {
        const haystack = [
          organization.name,
          organization.industry ?? '',
          organization.owner_name ?? '',
          organization.primary_contact_name ?? '',
          organization.primary_contact_email ?? '',
        ]
          .join(' ')
          .toLowerCase();

        return haystack.includes(search);
      });
    }

    const sorted = sortOrganizations(organizations, ordering);
    return HttpResponse.json(paginate(sorted, page, pageSize, url), { status: 200 });
  }),

  http.get(buildApiPath('/organizations/:organizationId/'), async ({ request, params }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const denied = requireOrganizationViewPermission(scenario);
    if (denied) {
      return denied;
    }

    if (scenario === 'organizations-error') {
      return HttpResponse.json(
        { code: 'MOCK_FAILURE', message: 'Simulated organization detail endpoint failure.' },
        { status: 500 },
      );
    }

    const organizationId = String(params.organizationId ?? '');
    const organization = getOrganizationDetailFixture(scenario, organizationId);

    if (!organization) {
      return HttpResponse.json(
        { code: 'NOT_FOUND', message: 'Organization not found.' },
        { status: 404 },
      );
    }

    return HttpResponse.json(organization, { status: 200 });
  }),

  http.post(buildApiPath('/organizations/'), async ({ request }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const session = getSessionFixture(scenario);
    if (!session) {
      return HttpResponse.json(
        { code: 'AUTH_REQUIRED', message: 'Authentication required.' },
        { status: 401 },
      );
    }

    if (!session.capabilities.includes('clients.create')) {
      return HttpResponse.json(
        { code: 'FORBIDDEN', message: 'You do not have permission to create organizations.' },
        { status: 403 },
      );
    }

    const body = (await request.json()) as OrganizationCreateRequest;
    const errors: Record<string, string[]> = {};

    if (!body.name || body.name.trim().length < 2) {
      errors.name = ['Organization name must be at least 2 characters long.'];
    }

    if (body.primary_contact_email && !body.primary_contact_email.includes('@')) {
      errors.primary_contact_email = ['Enter a valid email address.'];
    }

    if (Object.keys(errors).length) {
      return HttpResponse.json(
        {
          code: 'VALIDATION_ERROR',
          message: 'Please correct the highlighted fields.',
          errors,
        },
        { status: 400 },
      );
    }

    const created: OrganizationSummary = {
      id: `org_${crypto.randomUUID().slice(0, 8)}`,
      name: body.name.trim(),
      status: body.status ?? 'active',
      industry: body.industry ?? null,
      owner_name: session.user?.display_name ?? null,
      primary_contact_name: body.primary_contact_name ?? null,
      primary_contact_email: body.primary_contact_email ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return HttpResponse.json(created, { status: 201 });
  }),
];
