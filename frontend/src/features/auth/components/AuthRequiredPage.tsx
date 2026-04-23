import { Button } from '@/components/ui/Button';
import { env } from '@/lib/config/env';

export function AuthRequiredPage() {
  return (
    <div className="standalone-page">
      <div className="standalone-page__card">
        <p className="ui-page-header__eyebrow">Authentication required</p>
        <h1>Start from the central login portal</h1>
        <p>
          This tenant SPA assumes Django owns the root-domain sign-in flow and subdomain
          handoff. Sign in on the root domain first, then return here through the signed
          handoff flow.
        </p>
        <Button onClick={() => window.location.assign(env.rootLoginUrl)}>
          Go to root login
        </Button>
      </div>
    </div>
  );
}
