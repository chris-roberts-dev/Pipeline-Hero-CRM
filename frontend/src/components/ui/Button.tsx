import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

import '@/styles/ui.css';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps
  extends PropsWithChildren,
    ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({
  children,
  className = '',
  variant = 'primary',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`ui-button ui-button--${variant} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
