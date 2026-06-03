import { Users, UserPlus } from 'lucide-react';
import EmptyState from '../common/EmptyState.jsx';
import Button from '../common/Button.jsx';

export default function StudentEmptyState({ filtered, onCreate, canCreate }) {
  if (filtered) {
    return (
      <EmptyState
        icon={Users}
        title="No matching students"
        description="Try a different search term or clear the filter to see all students."
      />
    );
  }

  return (
    <EmptyState
      icon={Users}
      title="No students yet"
      description="Add a student to begin building the dataset for face recognition."
      action={
        canCreate ? (
          <Button onClick={onCreate}>
            <UserPlus size={16} />
            Add student
          </Button>
        ) : null
      }
    />
  );
}
