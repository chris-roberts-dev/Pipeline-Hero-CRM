import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../../lib/api/client';
import { useSession } from '../../session/useSession';

type HealthResponse = {
  status: string;
  mode: string;
};

export function DashboardPage() {
  const { session, hasCapability } = useSession();

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<HealthResponse>('/health/'),
  });

  return (
    <div className="grid gap-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-mph-primary">
          Session bootstrap active
        </p>

        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          Welcome back, {session.user?.fullName}
        </h1>

        <p className="mt-2 max-w-2xl text-slate-600">
          You are currently working in{' '}
          <span className="font-semibold">
            {session.activeOrganization?.name}
          </span>
          . The CRM shell is now session-aware and ready for feature slices.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Signed in as</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {session.user?.email}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Roles</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {session.membership?.roleNames.join(', ') || 'None'}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Mock API</p>

          {healthQuery.isLoading ? (
            <p className="mt-2 text-slate-500">Checking...</p>
          ) : healthQuery.isError ? (
            <p className="mt-2 text-red-600">Unavailable</p>
          ) : (
            <p className="mt-2 text-lg font-semibold text-slate-900">
              {healthQuery.data.status} · {healthQuery.data.mode}
            </p>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Capability checks
        </h2>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            'dashboard.view',
            'leads.view',
            'leads.create',
            'settings.manage',
          ].map((capability) => (
            <div
              key={capability}
              className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
            >
              <p className="text-sm font-medium text-slate-700">
                {capability}
              </p>
              <p
                className={[
                  'mt-1 text-sm font-semibold',
                  hasCapability(capability)
                    ? 'text-emerald-700'
                    : 'text-slate-400',
                ].join(' ')}
              >
                {hasCapability(capability) ? 'Allowed' : 'Not allowed'}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}