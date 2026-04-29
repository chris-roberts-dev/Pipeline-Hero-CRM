import type { Lead } from '@features/leads/schema';
import { Link } from 'react-router-dom';
import { LeadStatusBadge } from './LeadStatusBadge';

type LeadsTableProps = {
  leads: Lead[];
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

export function LeadsTable({ leads }: LeadsTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Lead
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Source
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Owner
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Market
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Est. Sales Price
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Updated
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 bg-white">
            {leads.map((lead) => (
              <tr key={lead.id} className="hover:bg-slate-50">
                <td className="px-4 py-4 align-top">
                  <Link
                    to={`/app/leads/${lead.id}`}
                    className="font-semibold text-mph-primary hover:text-mph-primary-hover hover:underline"
                  >
                    {lead.companyName}
                  </Link>
                  <p className="mt-1 text-sm text-slate-500">
                    {lead.leadNumber} · {lead.opportunityName}
                  </p>
                </td>

                <td className="px-4 py-4 align-top">
                  <LeadStatusBadge status={lead.status} />
                </td>

                <td className="px-4 py-4 align-top text-sm text-slate-700">
                  {lead.source}
                </td>

                <td className="px-4 py-4 align-top text-sm text-slate-700">
                  {lead.owner.name}
                </td>

                <td className="px-4 py-4 align-top text-sm text-slate-700">
                  {lead.market ?? '—'}
                  <p className="mt-1 text-xs text-slate-500">
                    {lead.location ?? 'No location'}
                  </p>
                </td>

                <td className="px-4 py-4 align-top text-sm font-semibold text-slate-900">
                  {formatCurrency(lead.estimatedSalesPrice)}
                </td>

                <td className="px-4 py-4 align-top text-sm text-slate-500">
                  {formatDate(lead.updatedAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}