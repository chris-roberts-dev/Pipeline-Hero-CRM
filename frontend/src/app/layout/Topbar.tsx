import { Badge } from '@/components/ui/Badge';
import { MessagesMenu } from '@/app/layout/topbar/MessagesMenu';
import { NotificationsMenu } from '@/app/layout/topbar/NotificationsMenu';
import { UserMenu } from '@/app/layout/topbar/UserMenu';
import { buildTopbarUser } from '@/app/layout/topbar/mockData';
import {
  useTopbarMessagesQuery,
  useTopbarNotificationsQuery,
} from '@/app/layout/topbar/queries';
import { MockScenarioSwitcher } from '@/features/devtools/components/MockScenarioSwitcher';
import { useTenant } from '@/features/tenant/TenantContext';

export function Topbar() {
  const { organization, session, hostSubdomain } = useTenant();
  const user = buildTopbarUser(session);
  const messagesQuery = useTopbarMessagesQuery();
  const notificationsQuery = useTopbarNotificationsQuery();

  return (
    <header className="app-topbar">
      <div className="app-topbar__context">
        <p className="app-topbar__eyebrow">Tenant workspace</p>
        <h2>{organization?.name ?? 'No active organization'}</h2>
      </div>

      <div className="app-topbar__meta">
        <MockScenarioSwitcher />
        {hostSubdomain ? <Badge>{hostSubdomain}</Badge> : null}
        {session?.impersonation.active ? <Badge tone="warning">Impersonating</Badge> : null}
        <div className="app-topbar__menus">
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
            errorMessage={notificationsQuery.isError ? 'Unable to load notifications.' : null}
          />
          <UserMenu user={user} onSignOut={() => window.alert('Replace with your sign-out flow.')} />
        </div>
      </div>
    </header>
  );
}
