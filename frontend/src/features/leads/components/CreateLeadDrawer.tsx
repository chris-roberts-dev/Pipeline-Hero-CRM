import { type SubmitEventHandler, useState } from 'react';
import { useCreateLeadMutation } from '../api/queries';
import type { CreateLeadPayload, LeadPriority } from '../types';

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
  estimatedValue: 0,
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

  if (!open) return null;

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

  function updateLocationAddressField<
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

  await createLeadMutation.mutateAsync({
    ...form,
    estimatedValue: Number(form.estimatedValue),
    region: form.region || null,
    market: form.market || null,
    location: form.location || null,
  });

  setForm(initialForm);
  onClose();
};


  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="create-lead-title">
        <div className="drawer-header">
          <div>
            <h2 id="create-lead-title">Create Lead</h2>
            <p>Add a new early-stage sales opportunity.</p>
          </div>

          <button type="button" className="drawer-close" onClick={onClose}>
            ×
          </button>
        </div>

        <form className="drawer-body" onSubmit={handleSubmit}>
          <section className="form-section">
            <h3>Lead Details</h3>

            <label>
              Company Name
              <input
                required
                value={form.companyName}
                onChange={(event) => updateField('companyName', event.target.value)}
              />
            </label>

            <label>
              Opportunity Name
              <input
                required
                value={form.opportunityName}
                onChange={(event) => updateField('opportunityName', event.target.value)}
              />
            </label>

            <div className="form-grid-two">
              <label>
                Source
                <select
                  value={form.source}
                  onChange={(event) => updateField('source', event.target.value)}
                >
                  <option>Website</option>
                  <option>Referral</option>
                  <option>Trade Show</option>
                  <option>Cold Outreach</option>
                  <option>Inbound Call</option>
                  <option>Partner</option>
                  <option>Existing Client</option>
                </select>
              </label>

              <label>
                Priority
                <select
                  value={form.priority}
                  onChange={(event) =>
                    updateField('priority', event.target.value as LeadPriority)
                  }
                >
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                  <option>Urgent</option>
                </select>
              </label>
            </div>

            <div className="form-grid-two">
              <label>
                Owner
                <input
                  required
                  value={form.ownerName}
                  onChange={(event) => updateField('ownerName', event.target.value)}
                  placeholder="Sarah Mitchell"
                />
              </label>

              <label>
                Estimated Value
                <input
                  type="number"
                  min="0"
                  required
                  value={form.estimatedValue}
                  onChange={(event) =>
                    updateField('estimatedValue', Number(event.target.value))
                  }
                />
              </label>
            </div>

            <label>
              Summary
              <textarea
                required
                rows={3}
                value={form.summary}
                onChange={(event) => updateField('summary', event.target.value)}
              />
            </label>
          </section>

          <section className="form-section">
            <h3>Operating Scope</h3>

            <div className="form-grid-three">
              <label>
                Region
                <input
                  value={form.region ?? ''}
                  onChange={(event) => updateField('region', event.target.value)}
                />
              </label>

              <label>
                Market
                <input
                  value={form.market ?? ''}
                  onChange={(event) => updateField('market', event.target.value)}
                />
              </label>

              <label>
                Location
                <input
                  value={form.location ?? ''}
                  onChange={(event) => updateField('location', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <h3>Primary Contact</h3>

            <div className="form-grid-two">
              <label>
                Name
                <input
                  required
                  value={form.contact.name}
                  onChange={(event) => updateContactField('name', event.target.value)}
                />
              </label>

              <label>
                Role / Title
                <input
                  value={form.contact.roleTitle}
                  onChange={(event) =>
                    updateContactField('roleTitle', event.target.value)
                  }
                />
              </label>
            </div>

            <div className="form-grid-two">
              <label>
                Email
                <input
                  type="email"
                  required
                  value={form.contact.email}
                  onChange={(event) => updateContactField('email', event.target.value)}
                />
              </label>

              <label>
                Phone
                <input
                  value={form.contact.phone}
                  onChange={(event) => updateContactField('phone', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <h3>Lead Location</h3>

            <label>
              Address Line 1
              <input
                required
                value={form.locationAddress.addressLine1}
                onChange={(event) =>
                  updateLocationAddressField('addressLine1', event.target.value)
                }
              />
            </label>

            <label>
              Address Line 2
              <input
                value={form.locationAddress.addressLine2 ?? ''}
                onChange={(event) =>
                  updateLocationAddressField('addressLine2', event.target.value)
                }
              />
            </label>

            <div className="form-grid-three">
              <label>
                City
                <input
                  required
                  value={form.locationAddress.city}
                  onChange={(event) =>
                    updateLocationAddressField('city', event.target.value)
                  }
                />
              </label>

              <label>
                State
                <input
                  required
                  value={form.locationAddress.state}
                  onChange={(event) =>
                    updateLocationAddressField('state', event.target.value)
                  }
                />
              </label>

              <label>
                Postal Code
                <input
                  required
                  value={form.locationAddress.postalCode}
                  onChange={(event) =>
                    updateLocationAddressField('postalCode', event.target.value)
                  }
                />
              </label>
            </div>

            <label>
              Location Notes
              <textarea
                rows={2}
                value={form.locationAddress.locationNotes ?? ''}
                onChange={(event) =>
                  updateLocationAddressField('locationNotes', event.target.value)
                }
              />
            </label>
          </section>

          {createLeadMutation.isError && (
            <div className="form-error">
              {createLeadMutation.error.message}
            </div>
          )}

          <div className="drawer-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>

            <button
              type="submit"
              className="btn-primary"
              disabled={createLeadMutation.isPending}
            >
              {createLeadMutation.isPending ? 'Creating...' : 'Create Lead'}
            </button>
          </div>
        </form>
      </aside>
    </div>
  );
}