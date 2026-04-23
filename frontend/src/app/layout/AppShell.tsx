import { Outlet } from 'react-router-dom';

import { SidebarNav } from '@/app/layout/SidebarNav';
import { Topbar } from '@/app/layout/Topbar';

export function AppShell() {
  return (
    <div className="app-shell">
      <SidebarNav />
      <div className="app-shell__content-wrap">
        <Topbar />
        <main className="app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
