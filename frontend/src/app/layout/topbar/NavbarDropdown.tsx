import { type ReactNode, useEffect, useId, useRef, useState } from 'react';

type NavbarDropdownProps = {
  trigger: ReactNode;
  children: ReactNode;
  align?: 'start' | 'end';
  panelClassName?: string;
};

export function NavbarDropdown({
  trigger,
  children,
  align = 'end',
  panelClassName,
}: NavbarDropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const panelId = useId();

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <div className="topbar-dropdown" ref={rootRef}>
      <button
        type="button"
        className="topbar-dropdown__trigger"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        {trigger}
      </button>

      {open ? (
        <div
          id={panelId}
          className={[
            'topbar-dropdown__menu',
            `topbar-dropdown__menu--${align}`,
            panelClassName ?? '',
          ]
            .filter(Boolean)
            .join(' ')}
          role="menu"
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}
