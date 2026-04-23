interface LoadingScreenProps {
  message?: string;
}

export function LoadingScreen({ message = 'Loading…' }: LoadingScreenProps) {
  return (
    <div className="ui-loading-screen" role="status" aria-live="polite">
      <div className="ui-spinner" />
      <span>{message}</span>
    </div>
  );
}
