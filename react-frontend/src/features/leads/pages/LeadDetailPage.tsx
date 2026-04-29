import { useLeadDetailQuery } from '@features/leads/api/queries';
import { LeadStatusBadge } from '@features/leads/components/LeadStatusBadge';
import { Link, useParams } from 'react-router-dom';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

export function LeadDetailPage() {
  const { leadId } = useParams();
  const leadQuery = useLeadDetailQuery(leadId);

  if (leadQuery.isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
        Loading lead...
      </div>
    );
  }

  if (leadQuery.isError || !leadQuery.data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-red-700">
          Lead could not be found.
        </p>
        <Link
          to="/app/leads"
          className="mt-3 inline-flex text-sm font-semibold text-mph-primary hover:underline"
        >
          Back to Leads
        </Link>
      </div>
    );
  }

  const lead = leadQuery.data;
  const primaryContact = lead.contacts[0];
  const primaryLocation = lead.locations[0];

  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link
            to="/app/leads"
            className="text-sm font-semibold text-mph-primary hover:underline"
          >
            ← Back to Leads
          </Link>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              {lead.companyName}
            </h1>
            <LeadStatusBadge status={lead.status} />
          </div>

          <p className="mt-1 text-sm text-slate-500">
            {lead.leadNumber} · {lead.opportunityName}
          </p>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Edit Lead
          </button>

          <button
            type="button"
            className="rounded-lg bg-mph-primary px-4 py-2 text-sm font-semibold text-white hover:bg-mph-primary-hover"
          >
            Convert to Quote
          </button>
        </div>
      </div>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Lead Summary</h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <DetailItem label="Lead Number" value={lead.leadNumber} />
            <DetailItem label="Status" value={lead.status} />
            <DetailItem label="Source" value={lead.source} />
            <DetailItem label="Owner" value={lead.owner.name} />
            <DetailItem
              label="Estimated Sales Price"
              value={formatCurrency(lead.estimatedSalesPrice)}
            />
            <DetailItem label="Priority" value={lead.priority} />
            <DetailItem
              label="Region / Market"
              value={`${lead.region ?? '—'} / ${lead.market ?? '—'}`}
            />
            <DetailItem label="Location" value={lead.location ?? '—'} />
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Description</h2>

          <p className="mt-4 text-sm leading-6 text-slate-600">
            {lead.summary}
          </p>

          <div className="mt-5 grid gap-2 border-t border-slate-200 pt-4 text-sm text-slate-500">
            <span>Created {formatDate(lead.createdAt)}</span>
            <span>Updated {formatDate(lead.updatedAt)}</span>
          </div>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Primary Contact
          </h2>

          {primaryContact ? (
            <div className="mt-4 rounded-xl bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                {primaryContact.name}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {primaryContact.roleTitle}
              </p>
              <p className="mt-3 text-sm text-slate-700">
                {primaryContact.email}
              </p>
              <p className="mt-1 text-sm text-slate-700">
                {primaryContact.phone}
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No contact attached.</p>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Lead Location
          </h2>

          {primaryLocation ? (
            <div className="mt-4 rounded-xl bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                {primaryLocation.addressLine1}
              </p>
              {primaryLocation.addressLine2 ? (
                <p className="text-sm text-slate-700">
                  {primaryLocation.addressLine2}
                </p>
              ) : null}
              <p className="mt-1 text-sm text-slate-700">
                {primaryLocation.city}, {primaryLocation.state}{' '}
                {primaryLocation.postalCode}
              </p>
              {primaryLocation.locationNotes ? (
                <p className="mt-3 text-sm text-slate-500">
                  {primaryLocation.locationNotes}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No location attached.</p>
          )}
        </article>
      </section>

      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Notes / Activity
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Activity timeline will be added in a later feature slice.
        </p>
      </section>
    </div>
  );
}

type DetailItemProps = {
  label: string;
  value: string;
};

function DetailItem({ label, value }: DetailItemProps) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 font-semibold text-slate-900">{value}</p>
    </div>
  );
}