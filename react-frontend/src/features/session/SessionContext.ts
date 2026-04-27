import { createContext } from 'react';
import type { SessionBootstrap } from './schema';

export type SessionContextValue = {
  session: SessionBootstrap;
  hasCapability: (capability: string) => boolean;
  hasRole: (role: string) => boolean;
};

export const SessionContext = createContext<SessionContextValue | null>(null);