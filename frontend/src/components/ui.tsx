import {
  type ButtonHTMLAttributes,
  forwardRef,
  type PropsWithChildren,
  type ReactNode,
  useEffect,
  useId,
  useRef,
} from "react";
import { AlertCircle, Inbox, LoaderCircle, X } from "lucide-react";

import type { User } from "../api/types";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  busy?: boolean;
}

export function Button({
  children,
  className = "",
  variant = "primary",
  busy = false,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      className={`button button--${variant} ${className}`}
      disabled={disabled || busy}
      {...props}
    >
      {busy ? <LoaderCircle className="spin" size={17} aria-hidden /> : null}
      {children}
    </button>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  active?: boolean;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton(
    { label, active = false, className = "", children, ...props },
    ref,
  ) {
    return (
      <button
        type="button"
        ref={ref}
        className={`icon-button ${active ? "is-active" : ""} ${className}`}
        aria-label={label}
        title={label}
        {...props}
      >
        {children}
      </button>
    );
  },
);

interface AvatarProps {
  user?: Pick<User, "username" | "avatar_url"> | null;
  name?: string;
  src?: string | null;
  size?: "small" | "medium" | "large" | "hero";
  online?: boolean;
}

export function Avatar({
  user,
  name,
  src,
  size = "medium",
  online,
}: AvatarProps) {
  const displayName = user?.username ?? name ?? "?";
  const image = user?.avatar_url ?? src;

  return (
    <span
      className={`avatar avatar--${size}`}
      aria-label={`${displayName}'s avatar`}
      role="img"
    >
      {image ? (
        <img src={image} alt="" />
      ) : (
        <span aria-hidden>{displayName.trim().slice(0, 2).toUpperCase()}</span>
      )}
      {online !== undefined ? (
        <i className={`presence ${online ? "is-online" : ""}`} aria-hidden />
      ) : null}
    </span>
  );
}

interface ModalProps extends PropsWithChildren {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  width?: "small" | "medium" | "large";
  footer?: ReactNode;
}

export function Modal({
  open,
  title,
  description,
  onClose,
  width = "medium",
  footer,
  children,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href]',
      );
      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.classList.remove("modal-open");
      previouslyFocused?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div
        ref={panelRef}
        className={`modal modal--${width}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="modal__header">
          <div>
            <h2 id={titleId}>{title}</h2>
            {description ? <p id={descriptionId}>{description}</p> : null}
          </div>
          <IconButton ref={closeRef} label="Close dialog" onClick={onClose}>
            <X size={19} />
          </IconButton>
        </header>
        <div className="modal__body">{children}</div>
        {footer ? <footer className="modal__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state state--loading" role="status">
      <LoaderCircle className="spin" size={24} aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="notice notice--error" role="alert">
      <AlertCircle size={18} aria-hidden />
      <span>{message}</span>
      {onRetry ? (
        <Button variant="ghost" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="state state--empty">
      <span className="state__icon">
        <Inbox size={24} aria-hidden />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
  controlId,
}: PropsWithChildren<{
  label: string;
  hint?: string;
  error?: string;
  controlId?: string;
}>) {
  const feedback = error ? (
    <span className="field__error" role="alert">
      {error}
    </span>
  ) : hint ? (
    <span className="field__hint">{hint}</span>
  ) : null;

  if (controlId) {
    return (
      <div className={`field ${error ? "field--error" : ""}`}>
        <label className="field__label" htmlFor={controlId}>
          {label}
        </label>
        {children}
        {feedback}
      </div>
    );
  }

  return (
    <label className={`field ${error ? "field--error" : ""}`}>
      <span className="field__label">{label}</span>
      {children}
      {feedback}
    </label>
  );
}
