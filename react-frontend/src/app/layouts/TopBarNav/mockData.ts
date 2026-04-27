import type { SessionBootstrap } from '../../../features/session/schema';
import type { TopbarUserSummary } from './types';

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

export function buildTopbarUser(
  session: SessionBootstrap | null | undefined,
): TopbarUserSummary {
  const displayName = session?.user?.fullName ?? 'Anonymous user';
  const isSupportUser = session?.user?.isSupportUser ?? false;

  const roleLabel = session?.impersonation?.active
    ? `Support session · acting as ${session.user?.email ?? 'tenant user'}`
    : isSupportUser
      ? 'Support user'
      : session?.membership?.roleNames?.join(', ') || 'Organization member';

  return {
    displayName,
    email: session?.user?.email ?? 'No email available',
    roleLabel,
    memberSinceLabel: isSupportUser ? 'Platform access' : 'Nov. 2023',
    organizationName: session?.activeOrganization?.name ?? null,
    avatarInitials: initialsFromName(displayName),
    profileHref: '#',
  };
}