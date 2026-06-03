import { CalendarX } from 'lucide-react';
import EmptyState from '../common/EmptyState.jsx';

export default function AttendanceEmptyState({ filtered }) {
  if (filtered) {
    return (
      <EmptyState
        icon={CalendarX}
        title="No matching records"
        description="No attendance found for the current filters. Try widening the date range or clearing the student filter."
      />
    );
  }
  return (
    <EmptyState
      icon={CalendarX}
      title="No attendance recorded yet"
      description="Start a session in Live Attendance — recognised students will appear here."
    />
  );
}
