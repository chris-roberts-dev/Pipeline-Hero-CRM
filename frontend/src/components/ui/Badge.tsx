interface BadgeProps {
  children: string;
  tone?: 'neutral' | 'success' | 'warning';
}

export function Badge({ children, tone = 'neutral' }: BadgeProps) {
  return <span className={`ui-badge ui-badge--${tone}`}>{children}</span>;
}
