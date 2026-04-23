interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
