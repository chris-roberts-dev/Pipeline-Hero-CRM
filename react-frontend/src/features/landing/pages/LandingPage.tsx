import { Link } from 'react-router-dom';

const previewStats = [
  ['New Leads', '24'],
  ['Open Quotes', '13'],
  ['Work Orders', '31'],
  ['Invoices Due', '$48.2k'],
];

const features = [
  {
    title: 'Pipeline you can trust',
    text: 'Stages, probabilities, and forecasts that stay accurate because next actions are built-in.',
  },
  {
    title: 'Follow-ups on autopilot',
    text: 'Automations that feel human: reminders, sequences, and task creation based on real events.',
  },
  {
    title: 'Contacts with context',
    text: 'Every note, call, email, and file — organized by account so anyone can pick up the thread.',
  },
  
  {
    title: 'Built for teams',
    text: 'Role-based access, multi-location support, and tidy reporting that doesn’t require a data team.',
  },
];

const pricingPlans = [
  {
    name: 'Solo',
    audience: 'For founders & freelancers',
    price: '$29',
    cadence: 'per month',
    description:
      'A focused CRM workspace for one person managing leads, follow-ups, and client history.',
    features: [
      '1 user',
      'Lead and contact management',
      'Pipeline snapshot',
      'Task reminders',
      'Basic reporting',
    ],
    cta: 'Start Solo',
    popular: false,
  },
  {
    name: 'Small Team',
    audience: 'For small teams collaborating daily',
    price: '$79',
    cadence: 'per month',
    description:
      'Shared CRM tools for teams that need visibility, ownership, and consistent follow-up.',
    features: [
      'Up to 5 users',
      'Shared pipeline workspace',
      'Team task management',
      'Customer activity history',
      'Role-based access basics',
    ],
    cta: 'Choose Small Team',
    popular: false,
  },
  {
    name: 'Growth',
    audience: 'For teams growing',
    price: '$149',
    cadence: 'per month',
    description:
      'Advanced pipeline, quoting, and workflow support for teams scaling their operations.',
    features: [
      'Up to 15 users',
      'Lead-to-quote workflow',
      'Quotes and order tracking',
      'Automation-ready follow-ups',
      'Advanced reporting views',
    ],
    cta: 'Choose Growth',
    popular: true,
  },
  {
    name: 'Scale',
    audience: 'For multi-team or multi-location orgs',
    price: 'Custom',
    cadence: 'tailored plan',
    description:
      'A flexible plan for larger organizations that need multi-location visibility and controls.',
    features: [
      'Unlimited team potential',
      'Multi-location support',
      'Advanced roles and permissions',
      'Platform support workflows',
      'Custom onboarding options',
    ],
    cta: 'Contact sales',
    popular: false,
  },
];

export function LandingPage() {
  return (
    <main>
      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <p className="mb-4 inline-flex rounded-full border border-teal-400/30 px-3 py-1 text-sm text-teal-200">
            Built for modern teams who want clarity, not chaos.
          </p>

          <h1 className="max-w-4xl text-5xl font-bold tracking-tight md:text-6xl">
            Run the full pipeline from lead to invoice.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            MyPipelineHero CRM keeps your pipeline, follow-ups, and customer history in one clean place — so your team moves faster, closes more, and never drops the ball.
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
        <div className="grid gap-4 md:grid-cols-4">
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
          <p className="text-sm font-semibold text-teal-200">How it works: Core Workflow</p>
          <h2 className="mt-2 text-3xl font-bold">Lead → Quote → Order → Fulfillment → Invoice</h2>
          <p className="mt-3 max-w-3xl text-slate-300">
            Start with a simple shell, then add each CRM module as a focused feature slice.
          </p>
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-7xl px-6 pb-20">
  <div className="mb-10 max-w-3xl">
    <p className="text-sm font-semibold text-teal-200">Pricing</p>
    <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">
      Plans that grow with your pipeline.
    </h2>
    <p className="mt-3 text-slate-300">
      Start with the CRM foundation you need today, then scale into team workflows,
      quoting, fulfillment, and multi-location visibility as your business grows.
    </p>
  </div>

  <div className="grid gap-5 lg:grid-cols-4">
    {pricingPlans.map((plan) => (
      <article
        key={plan.name}
        className={[
          'relative flex flex-col rounded-3xl border p-6 shadow-xl',
          plan.popular
            ? 'border-mph-primary bg-white text-slate-950 shadow-teal-950/30'
            : 'border-white/10 bg-white/5 text-white',
        ].join(' ')}
      >
        {plan.popular ? (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-mph-primary px-4 py-1 text-xs font-bold uppercase tracking-wide text-white">
            Most popular
          </div>
        ) : null}

        <div>
          <h3 className="text-xl font-bold">{plan.name}</h3>
          <p
            className={[
              'mt-1 text-sm',
              plan.popular ? 'text-slate-600' : 'text-slate-300',
            ].join(' ')}
          >
            {plan.audience}
          </p>
        </div>

        <div className="mt-6">
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold">{plan.price}</span>
            <span
              className={[
                'pb-1 text-sm',
                plan.popular ? 'text-slate-500' : 'text-slate-400',
              ].join(' ')}
            >
              {plan.cadence}
            </span>
          </div>

          <p
            className={[
              'mt-4 text-sm leading-6',
              plan.popular ? 'text-slate-600' : 'text-slate-300',
            ].join(' ')}
          >
            {plan.description}
          </p>
        </div>

        <ul className="mt-6 space-y-3">
          {plan.features.map((feature) => (
            <li
              key={feature}
              className={[
                'flex gap-2 text-sm',
                plan.popular ? 'text-slate-700' : 'text-slate-300',
              ].join(' ')}
            >
              <span
                className={[
                  'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                  plan.popular
                    ? 'bg-mph-primary text-white'
                    : 'bg-teal-400/10 text-teal-200',
                ].join(' ')}
              >
                ✓
              </span>
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        <Link
          to="/login"
          className={[
            'mt-8 inline-flex justify-center rounded-xl px-4 py-3 text-sm font-bold transition',
            plan.popular
              ? 'bg-mph-primary text-white hover:bg-mph-primary-dark'
              : 'border border-white/10 text-white hover:border-teal-300/50 hover:bg-white/10',
          ].join(' ')}
        >
          {plan.cta}
        </Link>
      </article>
    ))}
  </div>
</section>

    </main>
  );
}