import { useSession } from '../../../features/session/useSession';
import { MessagesMenu } from './MessagesMenu';
import { NotificationsMenu } from './NotificationsMenu';
import { UserMenu } from './UserMenu';
import { buildTopbarUser } from './mockData';
import {
  useTopbarMessagesQuery,
  useTopbarNotificationsQuery,
} from './queries';

export function Topbar() {
  const { session } = useSession();

  const user = buildTopbarUser(session);
  const messagesQuery = useTopbarMessagesQuery();
  const notificationsQuery = useTopbarNotificationsQuery();

  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div>
        <p className="text-sm font-medium text-slate-900">
          {session.activeOrganization?.name ?? 'No active organization'}
        </p>
        <p className="text-xs text-slate-500">
          {session.activeOrganization?.tenantDomain ?? 'Tenant portal'}
        </p>
      </div>

      <div className="flex items-center gap-3">
        {session.impersonation?.active ? (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
            Impersonating
          </span>
        ) : null}

        <MessagesMenu
          items={messagesQuery.data?.items ?? []}
          unreadCount={messagesQuery.data?.unreadCount ?? 0}
          isLoading={messagesQuery.isPending}
          errorMessage={messagesQuery.isError ? 'Unable to load messages.' : null}
        />

        <NotificationsMenu
          items={notificationsQuery.data?.items ?? []}
          unreadCount={notificationsQuery.data?.unreadCount ?? 0}
          isLoading={notificationsQuery.isPending}
          errorMessage={
            notificationsQuery.isError
              ? 'Unable to load notifications.'
              : null
          }
        />

        <UserMenu
          user={user}
          onSignOut={() => {
            window.alert('Replace with your real sign-out flow.');
          }}
        />
      </div>
    </header>
  );
}