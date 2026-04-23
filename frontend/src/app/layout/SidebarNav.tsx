import { useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

type NavLeaf = {
  label: string;
  to: string;
  disabled?: boolean;
};

type NavGroup = {
  label: string;
  children: NavLeaf[];
};

type NavItem = NavLeaf | NavGroup;

const items: NavItem[] = [
  { label: 'Dashboard', to: '/' },
  {
    label: 'Platform',
    children: [
      { label: 'Accounts', to: '/platform-accounts', disabled: true },
      { label: 'Organizations', to: '/organizations' },
      { label: 'Audits', to: '/audits', disabled: true },
    ],
  },
  {
    label: 'CRM',
    children: [
      { label: 'Leads', to: '/leads', disabled: true },
      { label: 'Quotes', to: '/quotes', disabled: true },
      { label: 'Clients', to: '/clients', disabled: true },
      { label: 'Orders', to: '/orders', disabled: true },
      { label: 'Tasks', to: '/tasks', disabled: true },
    ],
  },
  {
    label: 'Catalog',
    children: [
      { label: 'Services', to: '/services', disabled: true },
      { label: 'Products', to: '/products', disabled: true },
      { label: 'Manufacturing', to: '/manufacturing', disabled: true },
      { label: 'Materials', to: '/materials', disabled: true },
      { label: 'Pricing', to: '/pricing', disabled: true },
    ],
  },
  {
    label: 'Operations',
    children: [
      { label: 'Locations', to: '/locations', disabled: true },
      { label: 'Build Orders', to: '/build-orders', disabled: true },
      { label: 'Purchasing', to: '/purchasing', disabled: true },
      { label: 'Work Orders', to: '/work-orders', disabled: true },
    ],
  },
];

function isGroup(item: NavItem): item is NavGroup {
  return 'children' in item;
}

export function SidebarNav() {
  const { pathname } = useLocation();

  const defaultOpenGroups = useMemo(() => {
    return items
      .filter(isGroup)
      .reduce<Record<string, boolean>>((acc, item) => {
        acc[item.label] = item.children.some(
          (child) => pathname === child.to || pathname.startsWith(`${child.to}/`),
        );
        return acc;
      }, {});
  }, [pathname]);

  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(defaultOpenGroups);

  const toggleGroup = (label: string) => {
    setOpenGroups((current) => ({
      ...current,
      [label]: !current[label],
    }));
  };

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar__brand">
        <div className="app-sidebar__brand-mark">MP</div>
        <div>
          <strong>MyPipelineHero</strong>
          <p>CRM Portal</p>
        </div>
      </div>

      <nav className="app-sidebar__nav" aria-label="Primary navigation">
        {items.map((item) => {
          if (!isGroup(item)) {
            return item.disabled ? (
              <span key={item.label} className="app-sidebar__link app-sidebar__link--disabled">
                {item.label}
              </span>
            ) : (
              <NavLink
                key={item.label}
                to={item.to}
                className={({ isActive }) =>
                  `app-sidebar__link ${isActive ? 'app-sidebar__link--active' : ''}`.trim()
                }
                end={item.to === '/'}
              >
                {item.label}
              </NavLink>
            );
          }

          const isOpen = openGroups[item.label] ?? false;
          const panelId = `sidebar-group-${item.label.toLowerCase().replace(/\s+/g, '-')}`;
          const hasActiveChild = item.children.some(
            (child) => pathname === child.to || pathname.startsWith(`${child.to}/`),
          );

          return (
            <div key={item.label} className="app-sidebar__group">
              <button
                type="button"
                className={`app-sidebar__link app-sidebar__group-toggle ${
                  hasActiveChild ? 'app-sidebar__link--active' : ''
                }`.trim()}
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => toggleGroup(item.label)}
              >
                <span>{item.label}</span>
                <span className={`app-sidebar__chevron ${isOpen ? 'is-open' : ''}`}>▾</span>
              </button>

              {isOpen && (
                <div id={panelId} className="app-sidebar__group-children">
                  {item.children.map((child) =>
                    child.disabled ? (
                      <span
                        key={child.label}
                        className="app-sidebar__link app-sidebar__link--child app-sidebar__link--disabled"
                      >
                        {child.label}
                      </span>
                    ) : (
                      <NavLink
                        key={child.label}
                        to={child.to}
                        className={({ isActive }) =>
                          `app-sidebar__link app-sidebar__link--child ${
                            isActive ? 'app-sidebar__link--active' : ''
                          }`.trim()
                        }
                      >
                        {child.label}
                      </NavLink>
                    ),
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
