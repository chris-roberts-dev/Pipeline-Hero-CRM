import { useCreateLeadMutation } from '@features/leads/api/queries';
import {
    leadPriorities,
    leadSources,
    type CreateLeadPayload,
    type LeadPriority,
    type LeadSource,
} from '@features/leads/schema';
import { useState, type SubmitEventHandler } from 'react';

type CreateLeadDrawerProps = {
  open: boolean;
  onClose: () => void;
};

const initialForm: CreateLeadPayload = {
  companyName: '',
  opportunityName: '',
  source: 'Website',
  ownerName: '',
  region: '',
  market: '',
  location: '',
  estimatedSalesPrice: 0,
  priority: 'Medium',
  summary: '',
  contact: {
    name: '',
    email: '',
    phone: '',
    roleTitle: '',
  },
  locationAddress: {
    addressLine1: '',
    addressLine2: '',
    city: '',
    state: '',
    postalCode: '',
    locationNotes: '',
  },
};

export function CreateLeadDrawer({ open, onClose }: CreateLeadDrawerProps) {
  const [form, setForm] = useState<CreateLeadPayload>(initialForm);
  const createLeadMutation = useCreateLeadMutation();

  if (!open) {
    return null;
  }

  function updateField<K extends keyof CreateLeadPayload>(
    key: K,
    value: CreateLeadPayload[K],
  ) {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function updateContactField<K extends keyof CreateLeadPayload['contact']>(
    key: K,
    value: CreateLeadPayload['contact'][K],
  ) {
    setForm((current) => ({
      ...current,
      contact: {
        ...current.contact,
        [key]: value,
      },
    }));
  }

  function updateLocationField<
    K extends keyof CreateLeadPayload['locationAddress'],
  >(key: K, value: CreateLeadPayload['locationAddress'][K]) {
    setForm((current) => ({
      ...current,
      locationAddress: {
        ...current.locationAddress,
        [key]: value,
      },
    }));
  }

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();

    try {
      await createLeadMutation.mutateAsync({
        ...form,
        region: form.region || null,
        market: form.market || null,
        location: form.location || null,
        locationAddress: {
          ...form.locationAddress,
          addressLine2: form.locationAddress.addressLine2 || null,
          locationNotes: form.locationAddress.locationNotes || null,
        },
      });

      setForm(initialForm);
      onClose();
    } catch {
      // The mutation state renders the error below.
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex justify-end bg-slate-950/40">
      <aside
        className="flex h-screen w-full max-w-3xl flex-col bg-mph-shell shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-lead-title"
      >
        <div className="flex items-start justify-between border-b border-slate-200 bg-white px-6 py-5">
          <div>
            <h2 id="create-lead-title" className="text-xl font-bold text-slate-900">
              Create Lead
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Add a new early-stage sales opportunity.
            </p>
          </div>

          <button
            type="button"
            className="rounded-lg px-3 py-2 text-2xl leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            onClick={onClose}
            aria-label="Close create lead drawer"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                Lead Details
              </h3>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Company Name
                  <input
                    required
                    value={form.companyName}
                    onChange={(event) =>
                      updateField('companyName', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Opportunity Name
                  <input
                    required
                    value={form.opportunityName}
                    onChange={(event) =>
                      updateField('opportunityName', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Source
                  <select
                    value={form.source}
                    onChange={(event) =>
                      updateField('source', event.target.value as LeadSource)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  >
                    {leadSources.map((source) => (
                      <option key={source}>{source}</option>
                    ))}
                  </select>
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Priority
                  <select
                    value={form.priority}
                    onChange={(event) =>
                      updateField('priority', event.target.value as LeadPriority)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  >
                    {leadPriorities.map((priority) => (
                      <option key={priority}>{priority}</option>
                    ))}
                  </select>
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Owner
                  <input
                    required
                    value={form.ownerName}
                    placeholder="Alex Morgan"
                    onChange={(event) =>
                      updateField('ownerName', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Estimated Sales Price
                  <input
                    required
                    type="number"
                    min="0"
                    value={form.estimatedSalesPrice}
                    onChange={(event) =>
                      updateField(
                        'estimatedSalesPrice',
                        Number(event.target.value),
                      )
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>
              </div>

              <label className="mt-4 grid gap-1.5 text-sm font-medium text-slate-700">
                Summary
                <textarea
                  required
                  rows={3}
                  value={form.summary}
                  onChange={(event) => updateField('summary', event.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                />
              </label>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                Scope
              </h3>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Region
                  <input
                    value={form.region ?? ''}
                    onChange={(event) =>
                      updateField('region', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Market
                  <input
                    value={form.market ?? ''}
                    onChange={(event) =>
                      updateField('market', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Location
                  <input
                    value={form.location ?? ''}
                    onChange={(event) =>
                      updateField('location', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                Primary Contact
              </h3>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Name
                  <input
                    required
                    value={form.contact.name}
                    onChange={(event) =>
                      updateContactField('name', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Role / Title
                  <input
                    required
                    value={form.contact.roleTitle}
                    onChange={(event) =>
                      updateContactField('roleTitle', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Email
                  <input
                    required
                    type="email"
                    value={form.contact.email}
                    onChange={(event) =>
                      updateContactField('email', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Phone
                  <input
                    required
                    value={form.contact.phone}
                    onChange={(event) =>
                      updateContactField('phone', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                Lead Location
              </h3>

              <div className="mt-4 grid gap-4">
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Address Line 1
                  <input
                    required
                    value={form.locationAddress.addressLine1}
                    onChange={(event) =>
                      updateLocationField('addressLine1', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Address Line 2
                  <input
                    value={form.locationAddress.addressLine2 ?? ''}
                    onChange={(event) =>
                      updateLocationField('addressLine2', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>

                <div className="grid gap-4 md:grid-cols-3">
                  <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                    City
                    <input
                      required
                      value={form.locationAddress.city}
                      onChange={(event) =>
                        updateLocationField('city', event.target.value)
                      }
                      className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                    />
                  </label>

                  <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                    State
                    <input
                      required
                      value={form.locationAddress.state}
                      onChange={(event) =>
                        updateLocationField('state', event.target.value)
                      }
                      className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                    />
                  </label>

                  <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                    Postal Code
                    <input
                      required
                      value={form.locationAddress.postalCode}
                      onChange={(event) =>
                        updateLocationField('postalCode', event.target.value)
                      }
                      className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                    />
                  </label>
                </div>

                <label className="grid gap-1.5 text-sm font-medium text-slate-700">
                  Location Notes
                  <textarea
                    rows={2}
                    value={form.locationAddress.locationNotes ?? ''}
                    onChange={(event) =>
                      updateLocationField('locationNotes', event.target.value)
                    }
                    className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-mph-primary focus:ring-2 focus:ring-mph-primary/20"
                  />
                </label>
              </div>
            </section>

            {createLeadMutation.isError ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                Unable to create lead. Please review the fields and try again.
              </div>
            ) : null}
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={createLeadMutation.isPending}
              className="rounded-lg bg-mph-primary px-4 py-2 text-sm font-semibold text-white hover:bg-mph-primary-hover disabled:cursor-not-allowed disabled:opacity-70"
            >
              {createLeadMutation.isPending ? 'Creating...' : 'Create Lead'}
            </button>
          </div>
        </form>
      </aside>
    </div>
  );
}