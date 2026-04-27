import { z } from 'zod';

export const sessionUserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  fullName: z.string(),
  avatarUrl: z.string().nullable().optional(),
  isPlatformOwner: z.boolean(),
  isSupportUser: z.boolean(),
});

export const sessionOrganizationSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  tenantDomain: z.string().nullable().optional(),
});

export const sessionMembershipSchema = z.object({
  roleNames: z.array(z.string()),
  capabilityCodes: z.array(z.string()),
});

export const sessionImpersonationSchema = z.object({
  active: z.boolean(),
  originalActorId: z.string().nullable().optional(),
  originalActorName: z.string().nullable().optional(),
  reason: z.string().nullable().optional(),
});

export const sessionBootstrapSchema = z.object({
  isAuthenticated: z.boolean(),
  user: sessionUserSchema.nullable(),
  activeOrganization: sessionOrganizationSchema.nullable(),
  membership: sessionMembershipSchema.nullable(),
  impersonation: sessionImpersonationSchema.nullable(),
  featureFlags: z.record(z.string(), z.boolean()),
});

export type SessionBootstrap = z.infer<typeof sessionBootstrapSchema>;
export type SessionUser = z.infer<typeof sessionUserSchema>;
export type SessionOrganization = z.infer<typeof sessionOrganizationSchema>;
export type SessionMembership = z.infer<typeof sessionMembershipSchema>;