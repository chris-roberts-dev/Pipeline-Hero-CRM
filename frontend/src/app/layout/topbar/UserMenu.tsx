import { NavbarDropdown } from '@/app/layout/topbar/NavbarDropdown';
import { ChevronDownIcon } from '@/app/layout/topbar/icons';
import type { TopbarUserSummary } from '@/app/layout/topbar/types';

type UserMenuProps = {
  user: TopbarUserSummary;
  onSignOut?: () => void;
};

export function UserMenu({ user, onSignOut }: UserMenuProps) {
  return (
    <NavbarDropdown
      trigger={
        <span className="topbar-user-trigger">
          <span className="topbar-user-trigger__avatar" aria-hidden="true">
            {user.avatarInitials}
          </span>
          <span className="topbar-user-trigger__name">{user.displayName}</span>
          <ChevronDownIcon className="topbar-user-trigger__chevron" />
        </span>
      }
      panelClassName="topbar-dropdown__menu--user"
    >
      <div className="topbar-user-card">
        <div className="topbar-user-card__avatar" aria-hidden="true">
          {user.avatarInitials}
        </div>
        <p className="topbar-user-card__name">{user.displayName}</p>
        <p className="topbar-user-card__role">{user.roleLabel}</p>
        <p className="topbar-user-card__meta">Member since {user.memberSinceLabel}</p>
        {user.organizationName ? (
          <p className="topbar-user-card__meta">{user.organizationName}</p>
        ) : null}
      </div>

      <div className="topbar-user-card__body">
        <div className="topbar-user-card__row">
          <span className="topbar-user-card__label">Email</span>
          <span className="topbar-user-card__value">{user.email}</span>
        </div>
      </div>

      <div className="topbar-user-card__footer">
        <a href={user.profileHref ?? '#'} className="topbar-user-card__action topbar-user-card__action--secondary">
          Profile
        </a>
        <button
          type="button"
          className="topbar-user-card__action topbar-user-card__action--primary"
          onClick={onSignOut}
        >
          Sign out
        </button>
      </div>
    </NavbarDropdown>
  );
}
