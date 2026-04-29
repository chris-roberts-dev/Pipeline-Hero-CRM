import type { LeadStatus } from '@features/leads/schema';

type LeadStatusBadgeProps = {
  status: LeadStatus;
};

const statusStyles: Record<LeadStatus, string> = {
  New: 'bg-teal-50 text-mph-primary ring-teal-600/20',
  Contacted: 'bg-slate-100 text-slate-700 ring-slate-600/20',
  Qualified: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  Unqualified: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  Converted: 'bg-[#343a40] text-white ring-[#343a40]/20',
  Archived: 'bg-gray-100 text-gray-500 ring-gray-500/20',
};

export function LeadStatusBadge({ status }: LeadStatusBadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset',
        statusStyles[status],
      ].join(' ')}
    >
      {status}
    </span>
  );
}