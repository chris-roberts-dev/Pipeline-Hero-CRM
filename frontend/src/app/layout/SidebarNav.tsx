import { NavLink } from 'react-router-dom';

type NavItem = {
  label: string;
  to?: string;
  children?: { label: string; to: string }[];
};

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    children: [
      { label: 'Overview', to: '/' },
      { label: 'Analytics', to: '/analytics' },
    ],
  },
  {
    label: 'CRM',
    children: [
      { label: 'Leads', to: '/leads' },
      { label: 'Quotes', to: '/quotes' },
      { label: 'Clients', to: '/clients' },
      { label: 'Orders', to: '/orders' },
      { label: 'Communications', to: '/communications' },
      { label: 'Tasks', to: '/tasks' },
    ],
  },
  {
    label: 'Catalog',
    children: [
      { label: 'Products', to: '/products' },
      { label: 'Services', to: '/services' },
      { label: 'Materials', to: '/materials' },
      { label: 'Suppliers', to: '/suppliers' },
      { label: 'Manufacturing', to: '/manufacturing' },
    ],
  },
  {
    label: 'Apps',
    children: [
      { label: 'Mail', to: '/mail' },
      { label: 'Chat', to: '/chat' },
      { label: 'Files', to: '/files' },
      { label: 'Calendar', to: '/calendar' },
    ],
  },
  {
    label: 'System',
    children: [
      { label: 'Users', to: '/users' },
      { label: 'Notifications', to: '/notifications' },
      { label: 'Settings', to: '/settings' },
    ],
  },
];

export function SidebarNav() {
  return (
    <aside className="sidebar ">
      <div className="sidebar-brand">MyPipelineHero</div>

      <nav>
        {navItems.map((group) => (
          <div key={group.label} className="sidebar-group">
            <div className="sidebar-group-title">{group.label}</div>

            {group.children?.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}