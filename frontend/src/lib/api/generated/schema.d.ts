/**
 * Generated from contracts/internal-api.openapi.yaml.
 * Re-generate with `npm run openapi:types`.
 */

export interface components {
  schemas: {
    OrganizationSummary: {
      id: string;
      name: string;
      slug: string;
      timezone: string;
      base_currency_code: string;
    };
    AuthenticatedUser: {
      id: string;
      email: string;
      display_name: string;
      is_support_user: boolean;
    };
    ImpersonationState: {
      active: boolean;
      acting_as_email: string | null;
    };
    SessionBootstrap: {
      authenticated: boolean;
      organization: components['schemas']['OrganizationSummary'] | null;
      user: components['schemas']['AuthenticatedUser'] | null;
      capabilities: string[];
      impersonation: components['schemas']['ImpersonationState'];
    };
    TopbarMessageItem: {
      id: string;
      sender: string;
      preview: string;
      timeLabel: string;
      href: string;
      avatarInitials: string;
      starred: boolean;
      tone: 'danger' | 'warning' | 'neutral';
    };
    TopbarMessagesResponse: {
      unreadCount: number;
      items: components['schemas']['TopbarMessageItem'][];
    };
    TopbarNotificationItem: {
      id: string;
      label: string;
      timeLabel: string;
      href: string;
      icon: 'message' | 'people' | 'report' | 'alert';
    };
    TopbarNotificationsResponse: {
      unreadCount: number;
      items: components['schemas']['TopbarNotificationItem'][];
    };
    OrganizationActivityItem: {
      id: string;
      title: string;
      description: string;
      time_label: string;
    };
    OrganizationSummary: {
      id: string;
      name: string;
      status: 'active' | 'inactive';
      industry: string | null;
      owner_name: string | null;
      primary_contact_name: string | null;
      primary_contact_email: string | null;
      created_at: string;
      updated_at: string;
    };
    OrganizationDetail: components['schemas']['OrganizationSummary'] & {
      lifecycle_stage: 'lead' | 'prospect' | 'customer' | 'former_customer';
      employee_count: number | null;
      annual_revenue: number | null;
      website: string | null;
      phone: string | null;
      billing_address: string | null;
      service_address: string | null;
      notes: string;
      tags: string[];
      recent_activity: components['schemas']['OrganizationActivityItem'][];
    };
    OrganizationListResponse: {
      count: number;
      next: string | null;
      previous: string | null;
      results: components['schemas']['OrganizationSummary'][];
    };
    OrganizationCreateRequest: {
      name: string;
      status?: 'active' | 'inactive';
      industry?: string | null;
      primary_contact_name?: string | null;
      primary_contact_email?: string | null;
    };
    ErrorResponse: {
      code: string;
      message: string;
    };
    ValidationErrorResponse: {
      code: string;
      message: string;
      errors: Record<string, string[]>;
    };
  };
}

export interface paths {
  '/session/': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['SessionBootstrap'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
  };
  '/messages/summary/': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['TopbarMessagesResponse'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
  };
  '/notifications/summary/': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['TopbarNotificationsResponse'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
  };
  '/organizations/{organizationId}/': {
    get: {
      parameters: {
        path: {
          organizationId: string;
        };
      };
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['OrganizationDetail'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
        403: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
        404: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
  };
  '/organizations/': {
    get: {
      parameters: {
        query?: {
          page?: number;
          page_size?: number;
          search?: string;
          ordering?: 'name' | '-name' | 'updated_at' | '-updated_at';
          status?: 'active' | 'inactive';
        };
      };
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['OrganizationListResponse'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
        403: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
    post: {
      requestBody: {
        content: {
          'application/json': components['schemas']['OrganizationCreateRequest'];
        };
      };
      responses: {
        201: {
          content: {
            'application/json': components['schemas']['OrganizationSummary'];
          };
        };
        400: {
          content: {
            'application/json': components['schemas']['ValidationErrorResponse'];
          };
        };
        401: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
        403: {
          content: {
            'application/json': components['schemas']['ErrorResponse'];
          };
        };
      };
    };
  };
}
