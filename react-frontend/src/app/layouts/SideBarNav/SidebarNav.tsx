import { NavLink } from 'react-router-dom';

type NavItem = {
  label: string;
  to: string;
  disabled?: boolean;
};

type NavGroup = {
  label: string;
  children: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    label: 'Dashboard',
    children: [
      { label: 'Overview', to: '/app' },
      { label: 'Analytics', to: '/app/analytics'},
    ],
  },
  {
    label: 'CRM',
    children: [
      { label: 'Leads', to: '/app/leads' },
      { label: 'Quotes', to: '/app/quotes' },
      { label: 'Clients', to: '/app/clients' },
      { label: 'Orders', to: '/app/orders' },
      { label: 'Communications', to: '/app/communications' },
      { label: 'Tasks', to: '/app/tasks' },
    ],
  },
  {
    label: 'Catalog',
    children: [
      { label: 'Products', to: '/app/products' },
      { label: 'Services', to: '/app/services' },
      { label: 'Materials', to: '/app/materials' },
      { label: 'Suppliers', to: '/app/suppliers' },
      { label: 'Manufacturing', to: '/app/manufacturing' },
    ],
  },
  {
    label: 'Apps',
    children: [
      { label: 'Mail', to: '/app/mail' },
      { label: 'Chat', to: '/app/chat' },
      { label: 'Files', to: '/app/files' },
      { label: 'Calendar', to: '/app/calendar' },
    ],
  },
  {
    label: 'System',
    children: [
      { label: 'Users', to: '/app/users' },
      { label: 'Notifications', to: '/app/notifications' },
      { label: 'Settings', to: '/app/settings' },
    ],
  },
];

export function SidebarNav() {
  return (
    <aside className="fixed inset-y-0 left-0 hidden h-screen w-72 overflow-hidden border-r border-[#495057] bg-mph-sidebar text-slate-200 lg:flex lg:flex-col">
      <div className="shrink-0 border-b border-white/10 px-6 py-5">
        <div className="text-lg font-bold">MyPipelineHero</div>
        <p className="mt-1 text-xs">CRM Portal</p>
      </div>

      <nav className="sidebar-scrollbar min-h-0 flex-1 space-y-5 overflow-y-auto px-3 py-4"
  aria-label="Primary navigation">
        {navGroups.map((group) => (
          <section key={group.label}>
            <div className="px-3 font-semibold uppercase tracking-wider">
              {group.label}
            </div>

            <div className="">
              {group.children.map((item) =>
                item.disabled ? (
                  <span
                    key={item.to}
                    className="block cursor-not-allowed rounded-lg px-3 py-2 text-sm"
                  >
                    {item.label}
                  </span>
                ) : (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/app'}
                    className={({ isActive }) =>
                      [
                        'block rounded-lg px-3 py-2 text-sm font-medium transition',
                        isActive
                          ? 'bg-mph-primary text-white shadow-sm'
                          : 'text-slate-300 hover:bg-[#495057] hover:text-white',
                      ].join(' ')
                    }
                  >
                    {item.label}
                  </NavLink>
                ),
              )}
            </div>
          </section>
        ))}
      </nav>
    </aside>
  );
}