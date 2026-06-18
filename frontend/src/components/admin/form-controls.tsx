"use client";

/**
 * Small set of dark-themed form primitives used by the admin create/edit modals.
 * Loosely typed on purpose — admin payloads are heterogeneous.
 */

const fieldBase =
  "w-full rounded-md border border-grid bg-card2 px-3 py-2 font-mono text-[13px] text-ink " +
  "placeholder:text-ink-muted focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan/40 " +
  "transition-colors";

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-ink-muted">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-ink-muted">{hint}</span>}
    </label>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${fieldBase} ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`${fieldBase} cursor-pointer appearance-none ${props.className ?? ""}`}
    />
  );
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between rounded-md border border-grid bg-card2 px-3 py-2 text-left transition-colors hover:border-grid"
    >
      <span className="font-mono text-[12px] text-ink">{label}</span>
      <span
        className="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors"
        style={{
          background: checked ? "#00FF88" : "#0D1F35",
          boxShadow: checked ? "0 0 8px rgba(0,255,136,0.4)" : "none",
        }}
      >
        <span
          className="inline-block h-3.5 w-3.5 transform rounded-full bg-app transition-transform"
          style={{ transform: checked ? "translateX(18px)" : "translateX(3px)" }}
        />
      </span>
    </button>
  );
}

export function Button({
  variant = "secondary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const styles: Record<string, string> = {
    primary:
      "bg-cyan text-app hover:opacity-90 shadow-glow-cyan font-semibold",
    secondary:
      "border border-grid bg-card2 text-ink hover:border-cyan/50 hover:text-cyan",
    danger:
      "border border-[#FF2D55]/40 bg-[#FF2D55]/10 text-[#FF2D55] hover:bg-[#FF2D55]/20",
  };
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 font-mono text-[12px] uppercase tracking-wider transition-all disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${props.className ?? ""}`}
    />
  );
}
