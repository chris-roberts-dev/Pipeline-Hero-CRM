import { Link, Outlet } from 'react-router-dom';

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link to="/" className="text-xl font-bold tracking-tight">
          MyPipelineHero
        </Link>

        <nav className="flex items-center gap-4 text-sm text-slate-300">
          <a href="#features" className="hover:text-white">
            Features
          </a>
          <a href="#workflow" className="hover:text-white">
            Workflow
          </a>
          <a href="#pricing" className="hover:text-white">
            Pricing
          </a>
          <Link
            to="/login"
            className="rounded-lg bg-mph-primary px-4 py-2 font-semibold text-white hover:bg-mph-primary-dark"
          >
            Sign in
          </Link>
        </nav>
      </header>

      <Outlet />
    </div>
  );
}