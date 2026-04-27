import { Link } from 'react-router-dom';

const previewStats = [
  ['New Leads', '24'],
  ['Open Quotes', '13'],
  ['Work Orders', '31'],
  ['Invoices Due', '$48.2k'],
];

const features = [
  {
    title: 'Tenant-aware CRM',
    text: 'Keep every tenant organization isolated, permission-scoped, and audit-friendly.',
  },
  {
    title: 'Quote to fulfillment',
    text: 'Move from lead to quote to order, then into work orders, purchase orders, or build orders.',
  },
  {
    title: 'Billing-ready workflow',
    text: 'Track invoices, payment progress, and operational handoffs without losing context.',
  },
];

export function LandingPage() {
  return (
    <main>
      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <p className="mb-4 inline-flex rounded-full border border-teal-400/30 px-3 py-1 text-sm text-teal-200">
            CRM + quoting + fulfillment in one workflow
          </p>

          <h1 className="max-w-4xl text-5xl font-bold tracking-tight md:text-6xl">
            Run the full pipeline from lead to invoice.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            MyPipelineHero helps service, product, and manufacturing teams manage leads,
            quotes, orders, work execution, purchasing, builds, invoices, and payments
            from one tenant-aware CRM.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/login"
              className="rounded-xl bg-mph-primary px-5 py-3 font-semibold text-white shadow-lg shadow-teal-950/40 hover:bg-mph-primary-dark"
            >
              Sign in
            </Link>

            <a
              href="#features"
              className="rounded-xl border border-slate-700 px-5 py-3 font-semibold text-slate-200 hover:border-slate-500"
            >
              View features
            </a>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/10 p-4 shadow-2xl">
          <div className="rounded-2xl bg-slate-900 p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Pipeline Snapshot</p>
                <h2 className="text-2xl font-semibold">April Overview</h2>
              </div>
              <span className="rounded-full bg-teal-400/10 px-3 py-1 text-sm text-teal-200">
                Demo
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {previewStats.map(([label, value]) => (
                <div key={label} className="rounded-2xl bg-white/5 p-4">
                  <p className="text-sm text-slate-400">{label}</p>
                  <p className="mt-2 text-2xl font-bold">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-6 pb-20">
        <div className="grid gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <h3 className="font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="workflow" className="mx-auto max-w-7xl px-6 pb-24">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8">
          <p className="text-sm font-semibold text-teal-200">Core workflow</p>
          <h2 className="mt-2 text-3xl font-bold">Lead → Quote → Order → Fulfillment → Invoice</h2>
          <p className="mt-3 max-w-3xl text-slate-300">
            Start with a simple shell, then add each CRM module as a focused feature slice.
          </p>
        </div>
      </section>
    </main>
  );
}