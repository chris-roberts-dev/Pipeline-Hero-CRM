import { NavbarDropdown } from './NavbarDropdown';
import { BellIcon, MessageIcon, PeopleIcon, ReportIcon } from './icons';
import type { TopbarNotificationItem } from './types';

type NotificationsMenuProps = {
  items: TopbarNotificationItem[];
  unreadCount: number;
  isLoading?: boolean;
  errorMessage?: string | null;
};

function NotificationLeadingIcon({ icon }: { icon: TopbarNotificationItem['icon'] }) {
  switch (icon) {
    case 'people':
      return <PeopleIcon className="topbar-notification-item__icon" />;
    case 'report':
      return <ReportIcon className="topbar-notification-item__icon" />;
    case 'alert':
      return <BellIcon className="topbar-notification-item__icon" />;
    case 'message':
    default:
      return <MessageIcon className="topbar-notification-item__icon" />;
  }
}

export function NotificationsMenu({
  items,
  unreadCount,
  isLoading = false,
  errorMessage = null,
}: NotificationsMenuProps) {
  return (
    <NavbarDropdown
      trigger={
        <span className="topbar-icon-button__content">
          <span className="topbar-icon-button__icon-wrap">
            <BellIcon className="topbar-icon-button__icon" />
            {unreadCount > 0 ? (
              <span className="topbar-count-badge topbar-count-badge--warning">{unreadCount}</span>
            ) : null}
          </span>
          <span className="topbar-icon-button__label sr-only">Notifications</span>
        </span>
      }
      panelClassName="topbar-dropdown__menu--notifications"
    >
      <div className="topbar-menu-header">{unreadCount} Notifications</div>
      <div className="topbar-menu-divider" />

      {isLoading ? (
        <div className="topbar-menu-empty">Loading notifications…</div>
      ) : errorMessage ? (
        <div className="topbar-menu-empty topbar-menu-empty--error">{errorMessage}</div>
      ) : items.length === 0 ? (
        <div className="topbar-menu-empty">No new notifications.</div>
      ) : (
        <>
          {items.map((item, index) => (
            <div key={item.id}>
              <a href={item.href} className="topbar-notification-item">
                <span className="topbar-notification-item__leading">
                  <NotificationLeadingIcon icon={item.icon} />
                </span>
                <span className="topbar-notification-item__label">{item.label}</span>
                <span className="topbar-notification-item__time">{item.timeLabel}</span>
              </a>
              {index < items.length - 1 ? <div className="topbar-menu-divider" /> : null}
            </div>
          ))}

          <div className="topbar-menu-divider" />
          <a href="#" className="topbar-menu-footer-link">
            See all notifications
          </a>
        </>
      )}
    </NavbarDropdown>
  );
}
