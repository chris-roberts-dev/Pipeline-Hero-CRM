import type { SessionBootstrap } from '@/lib/auth/types';
import type { TopbarUserSummary } from '@/app/layout/topbar/types';

function initialsFromName(name: string | null | undefined): string {
  if (!name) return 'MP';

  const parts = name
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) return 'MP';

  return parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
}

export function buildTopbarUser(session: SessionBootstrap | null | undefined): TopbarUserSummary {
  const displayName = session?.user?.display_name ?? 'Anonymous user';
  const isSupportUser = session?.user?.is_support_user ?? false;
  const roleLabel = session?.impersonation.active
    ? `Support session · acting as ${session.impersonation.acting_as_email ?? 'tenant user'}`
    : isSupportUser
      ? 'Support user'
      : 'Organization member';

  return {
    displayName,
    email: session?.user?.email ?? 'No email available',
    roleLabel,
    memberSinceLabel: isSupportUser ? 'Platform access' : 'Nov. 2023',
    organizationName: session?.organization?.name ?? null,
    avatarInitials: initialsFromName(displayName),
    profileHref: '#',
  };
}
