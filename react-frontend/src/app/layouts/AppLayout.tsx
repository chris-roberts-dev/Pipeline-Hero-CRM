import { Outlet } from 'react-router-dom';
import { SessionProvider } from '../../features/session/SessionProvider';
import { SidebarNav } from './SideBarNav/SidebarNav';
import { Topbar } from './TopBarNav/Topbar';

export function AppLayout() {
  return (
    <SessionProvider>
      <AuthenticatedAppShell />
    </SessionProvider>
  );
}

function AuthenticatedAppShell() {
  return (
    <div className="min-h-screen bg-slate-100">
      <SidebarNav />

      <div className="lg:pl-72">
        <Topbar />

        <main className="p-6">
          <Outlet />

        </main>

      </div>
    </div>
  );
}