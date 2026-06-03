import { useEffect, useState } from 'react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import FormInput from '../common/FormInput.jsx';
import FormError from '../common/FormError.jsx';
import { fetchClasses } from '../../services/classService.js';

const EMPTY = {
  name: '',
  roll_number: '',
  department: '',
  email: '',
  phone: '',
  class_id: '',
};

function toFormValues(student) {
  if (!student) return EMPTY;
  return {
    name: student.name ?? '',
    roll_number: student.roll_number ?? '',
    department: student.department ?? '',
    email: student.email ?? '',
    phone: student.phone ?? '',
    class_id: student.class_id != null ? String(student.class_id) : '',
  };
}

/**
 * Used for both create and edit; the parent decides which by passing `student`.
 * Diffs the form against the original on edit so PATCH payloads stay minimal —
 * the backend treats undefined fields as "leave unchanged."
 */
export default function StudentFormModal({
  open,
  mode = 'create', // 'create' | 'edit'
  student,
  defaultClassId,
  onClose,
  onSubmit,
}) {
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [classList, setClassList] = useState([]);

  // Load available classes when the modal opens.
  useEffect(() => {
    if (open) {
      const initial = toFormValues(student);
      // Pre-fill class from active context on create when no class is set.
      if (mode === 'create' && !initial.class_id && defaultClassId) {
        initial.class_id = String(defaultClassId);
      }
      setValues(initial);
      setErrors({});
      setFormError(null);
      setSubmitting(false);
      fetchClasses({ activeOnly: true })
        .then((r) => setClassList(r.items ?? []))
        .catch(() => setClassList([]));
    }
  }, [open, student, mode, defaultClassId]);

  const set = (key) => (e) => {
    setValues((v) => ({ ...v, [key]: e.target.value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const validate = () => {
    const next = {};
    if (!values.name.trim()) next.name = 'Required';
    if (!values.roll_number.trim()) next.roll_number = 'Required';
    if (values.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.email)) {
      next.email = 'Invalid email';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const buildPayload = () => {
    const trimmed = {
      name: values.name.trim(),
      roll_number: values.roll_number.trim(),
      department: values.department.trim() || null,
      email: values.email.trim() || null,
      phone: values.phone.trim() || null,
      class_id: values.class_id ? parseInt(values.class_id, 10) : null,
    };
    if (mode === 'create') return trimmed;

    // PATCH — only include fields that actually changed.
    const diff = {};
    const original = toFormValues(student);
    for (const k of Object.keys(trimmed)) {
      if (k === 'class_id') {
        const origVal = student?.class_id ?? null;
        if (trimmed.class_id !== origVal) diff.class_id = trimmed.class_id;
        continue;
      }
      const before = original[k]?.trim?.() || null;
      if ((trimmed[k] ?? null) !== before) diff[k] = trimmed[k];
    }
    return diff;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    const payload = buildPayload();
    if (mode === 'edit' && Object.keys(payload).length === 0) {
      onClose();
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setFormError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const title = mode === 'edit' ? 'Edit student' : 'Add student';
  const subtitle =
    mode === 'edit'
      ? 'Update profile fields. Dataset is managed separately.'
      : 'Create a profile. Upload dataset images after saving.';

  return (
    <BaseModal
      open={open}
      onClose={submitting ? undefined : onClose}
      title={title}
      subtitle={subtitle}
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <LoadingButton
            loading={submitting}
            onClick={handleSubmit}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            {mode === 'edit' ? 'Save changes' : 'Create student'}
          </LoadingButton>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-3" noValidate>
        <FormError message={formError && resolveError(formError)} />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormInput
            id="student-name"
            label="Full name"
            required
            autoFocus
            value={values.name}
            onChange={set('name')}
            error={errors.name}
            maxLength={128}
          />
          <FormInput
            id="student-roll"
            label="Roll number"
            required
            value={values.roll_number}
            onChange={set('roll_number')}
            error={errors.roll_number}
            maxLength={32}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormInput
            id="student-department"
            label="Department"
            value={values.department}
            onChange={set('department')}
            error={errors.department}
            maxLength={64}
          />
          <div>
            <label htmlFor="student-class" className="block text-xs font-medium text-zinc-400 mb-1">
              Class
            </label>
            <select
              id="student-class"
              value={values.class_id}
              onChange={set('class_id')}
              className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="">Unassigned</option>
              {classList.map((c) => (
                <option key={c.id} value={c.id}>{c.class_code}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormInput
            id="student-email"
            label="Email"
            type="email"
            value={values.email}
            onChange={set('email')}
            error={errors.email}
          />
          <FormInput
            id="student-phone"
            label="Phone"
            value={values.phone}
            onChange={set('phone')}
            error={errors.phone}
            maxLength={32}
          />
        </div>

        {/* Hidden submit so Enter inside an input still submits the form. */}
        <button type="submit" className="hidden" />
      </form>
    </BaseModal>
  );
}

function resolveError(err) {
  const payload = err?.response?.data;
  if (payload?.message) return payload.message;
  if (payload?.errors?.[0]?.message) return payload.errors[0].message;
  if (err?.message) return err.message;
  return 'Could not save the student.';
}
