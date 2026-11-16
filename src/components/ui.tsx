import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "ghost" | "danger";
    compact?: boolean;
  }
>(function Button(
  { variant = "ghost", compact, children, className = "", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`button ${variant} ${compact ? "compact" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
});
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="modal-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                className="modal glass"
                data-material="modal"
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.18 }}
              >
                <div className="row between">
                  <Dialog.Title>{title}</Dialog.Title>
                  <Dialog.Close asChild>
                    <Button compact aria-label="關閉">
                      <X size={18} />
                    </Button>
                  </Dialog.Close>
                </div>
                <Dialog.Description className="muted">
                  {description}
                </Dialog.Description>
                {children}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
export function Slider({
  label,
  value,
  min = 0,
  max = 100,
  unit = "%",
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="slider-control">
      <span className="row between">
        <span>{label}</span>
        <output>
          {value}
          {unit}
        </output>
      </span>
      <input
        aria-label={label}
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(+e.target.value)}
      />
    </label>
  );
}
export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="toggle-row">
      <span>
        <span>{label}</span>
        {description && <small>{description}</small>}
      </span>
      <input
        role="switch"
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="toggle-track" />
    </label>
  );
}
