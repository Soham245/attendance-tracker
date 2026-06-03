import { AlertTriangle } from 'lucide-react';
import BaseModal from './BaseModal.jsx';
import Button from './Button.jsx';
import LoadingButton from './LoadingButton.jsx';

const TONES = {
  danger: 'text-rose-300 bg-rose-500/10 ring-rose-500/30',
  warning: 'text-amber-300 bg-amber-500/10 ring-amber-500/30',
  info: 'text-accent bg-accent/10 ring-accent/30',
};

const BUTTONS = {
  danger: 'bg-rose-600 hover:bg-rose-500 text-white',
  warning: 'bg-amber-600 hover:bg-amber-500 text-white',
  info: 'bg-accent hover:bg-accent-hover text-white',
};

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  description,
  tone = 'danger',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  loading = false,
  error,
}) {
  return (
    <BaseModal
      open={open}
      onClose={loading ? undefined : onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <LoadingButton
            loading={loading}
            onClick={onConfirm}
            className={BUTTONS[tone] ?? BUTTONS.danger}
          >
            {confirmLabel}
          </LoadingButton>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <div
          className={`grid place-items-center h-9 w-9 rounded-full ring-1 ${
            TONES[tone] ?? TONES.danger
          }`}
        >
          <AlertTriangle size={18} />
        </div>
        <div className="text-sm text-zinc-300 leading-relaxed">
          {description}
          {error ? (
            <div className="mt-2 text-rose-300 text-xs">{error}</div>
          ) : null}
        </div>
      </div>
    </BaseModal>
  );
}
