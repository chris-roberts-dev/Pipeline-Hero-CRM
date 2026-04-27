import { Link } from 'react-router-dom';

export function LoginRedirectPage() {
  return (
    <main className="mx-auto max-w-xl px-6 py-24">
      <div className="rounded-3xl border border-white/10 bg-white/10 p-8">
        <h1 className="text-3xl font-bold">Sign in</h1>
        <p className="mt-3 text-slate-300">
          For now, this is a placeholder. Later, this can redirect to your Django-backed
          auth flow or become the frontend entry point for authentication.
        </p>

        <Link
          to="/app"
          className="mt-6 inline-flex rounded-xl bg-mph-primary px-5 py-3 font-semibold text-white hover:bg-mph-primary-dark"
        >
          Continue to app shell
        </Link>
      </div>
    </main>
  );
}