import { NavbarDropdown } from '@/app/layout/topbar/NavbarDropdown';
import { ClockIcon, MessageIcon, StarIcon } from '@/app/layout/topbar/icons';
import type { TopbarMessageItem } from '@/app/layout/topbar/types';

type MessagesMenuProps = {
  items: TopbarMessageItem[];
  unreadCount: number;
  isLoading?: boolean;
  errorMessage?: string | null;
};

export function MessagesMenu({ items, unreadCount, isLoading = false, errorMessage = null }: MessagesMenuProps) {
  return (
    <NavbarDropdown
      trigger={
        <span className="topbar-icon-button__content">
          <span className="topbar-icon-button__icon-wrap">
            <MessageIcon className="topbar-icon-button__icon" />
            {unreadCount > 0 ? (
              <span className="topbar-count-badge topbar-count-badge--danger">{unreadCount}</span>
            ) : null}
          </span>
          <span className="topbar-icon-button__label sr-only">Messages</span>
        </span>
      }
      panelClassName="topbar-dropdown__menu--messages"
    >
      <div className="topbar-menu-section">
        {isLoading ? (
          <div className="topbar-menu-empty">Loading messages…</div>
        ) : errorMessage ? (
          <div className="topbar-menu-empty topbar-menu-empty--error">{errorMessage}</div>
        ) : items.length === 0 ? (
          <div className="topbar-menu-empty">No new messages.</div>
        ) : (
          <>
            {items.map((item, index) => (
              <div key={item.id}>
                <a href={item.href} className="topbar-message-item">
                  <div className="topbar-message-item__avatar" aria-hidden="true">
                    {item.avatarInitials}
                  </div>

                  <div className="topbar-message-item__body">
                    <div className="topbar-message-item__header">
                      <strong>{item.sender}</strong>
                      {item.starred ? (
                        <span className={`topbar-message-item__star topbar-message-item__star--${item.tone}`}>
                          <StarIcon className="topbar-message-item__star-icon" />
                        </span>
                      ) : null}
                    </div>

                    <p>{item.preview}</p>

                    <span className="topbar-message-item__time">
                      <ClockIcon className="topbar-message-item__clock" />
                      {item.timeLabel}
                    </span>
                  </div>
                </a>
                {index < items.length - 1 ? <div className="topbar-menu-divider" /> : null}
              </div>
            ))}

            <div className="topbar-menu-divider" />
            <a href="#" className="topbar-menu-footer-link">
              See all messages
            </a>
          </>
        )}
      </div>
    </NavbarDropdown>
  );
}
