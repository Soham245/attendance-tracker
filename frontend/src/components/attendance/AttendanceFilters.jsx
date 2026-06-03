import { FilterX } from 'lucide-react';
import Button from '../common/Button.jsx';
import FormInput from '../common/FormInput.jsx';

/**
 * Filters are local input state owned by the parent. Apply only fires on
 * submit (or explicit clear) so we don't spam the backend on every keystroke.
 */
export default function AttendanceFilters({
  values,
  onChange,
  onApply,
  onClear,
  loading,
}) {
  const set = (key) => (e) =>
    onChange({ ...values, [key]: e.target.value });

  const hasFilters = Boolean(values.studentId || values.onDate);

  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(e) => {
        e.preventDefault();
        onApply();
      }}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:flex-1">
        <FormInput
          id="filter-student"
          label="Student ID"
          type="number"
          inputMode="numeric"
          min={1}
          placeholder="e.g. 42"
          value={values.studentId}
          onChange={set('studentId')}
          hint="optional"
        />
        <FormInput
          id="filter-date"
          label="Date"
          type="date"
          value={values.onDate}
          onChange={set('onDate')}
          hint="optional"
        />
      </div>
      <div className="flex items-end gap-2">
        <Button type="submit" loading={loading} disabled={loading}>
          Apply
        </Button>
        {hasFilters ? (
          <Button variant="ghost" onClick={onClear} disabled={loading}>
            <FilterX size={14} />
            Clear
          </Button>
        ) : null}
      </div>

    </form>
  );
}
