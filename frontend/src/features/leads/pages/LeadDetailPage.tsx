import { Link, useParams } from 'react-router-dom';
import { useLeadDetailQuery } from '../api/queries';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function LeadDetailPage() {
  const { leadId } = useParams();
  const leadQuery = useLeadDetailQuery(leadId);

  if (leadQuery.isLoading) {
    return <div className="empty-state">Loading lead...</div>;
  }

  if (leadQuery.isError || !leadQuery.data) {
    return (
      <div className="empty-state empty-state--error">
        Lead could not be found.
      </div>
    );
  }

  const lead = leadQuery.data;

  return (
    <div className="page-stack">
      <div className="content-header">
        <div>
          <Link to="/leads" className="back-link">
            ← Back to Leads
          </Link>
          <h1>{lead.companyName}</h1>
          <p>{lead.opportunityName}</p>
        </div>

        <div className="header-actions">
          <button type="button" className="btn-secondary">
            Edit Lead
          </button>
          <button type="button" className="btn-primary">
            Convert to Quote
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <section className="card">
          <div className="card-header">
            <h2>Lead Summary</h2>
          </div>

          <div className="detail-list">
            <div>
              <span>Lead Number</span>
              <strong>{lead.leadNumber}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{lead.status}</strong>
            </div>
            <div>
              <span>Source</span>
              <strong>{lead.source}</strong>
            </div>
            <div>
              <span>Owner</span>
              <strong>{lead.owner.name}</strong>
            </div>
            <div>
              <span>Estimated Value</span>
              <strong>{formatCurrency(lead.estimatedValue)}</strong>
            </div>
            <div>
              <span>Priority</span>
              <strong>{lead.priority}</strong>
            </div>
            <div>
              <span>Region / Market</span>
              <strong>{lead.region} / {lead.market}</strong>
            </div>
            <div>
              <span>Location</span>
              <strong>{lead.location}</strong>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Description</h2>
          </div>

          <p className="detail-description">{lead.summary}</p>

          <div className="detail-meta">
            <span>Created {new Date(lead.createdAt).toLocaleDateString()}</span>
            <span>Updated {new Date(lead.updatedAt).toLocaleDateString()}</span>
          </div>
        </section>
      </div>

      <div className="detail-grid">
        <section className="card">
          <div className="card-header">
            <h2>Contacts</h2>
          </div>

          <div className="stack-list">
            {lead.contacts.map((contact) => (
              <div key={contact.id} className="stack-list-item">
                <strong>{contact.name}</strong>
                <span>{contact.roleTitle}</span>
                <span>{contact.email}</span>
                <span>{contact.phone}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Locations</h2>
          </div>

          <div className="stack-list">
            {lead.locations.map((location) => (
              <div key={location.id} className="stack-list-item">
                <strong>{location.addressLine1}</strong>
                {location.addressLine2 && <span>{location.addressLine2}</span>}
                <span>
                  {location.city}, {location.state} {location.postalCode}
                </span>
                {location.locationNotes && <span>{location.locationNotes}</span>}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}