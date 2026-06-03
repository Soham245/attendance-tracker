import { ImageOff } from 'lucide-react';
import DatasetImageCard from './DatasetImageCard.jsx';
import EmptyState from '../common/EmptyState.jsx';

export default function DatasetGallery({
  images,
  loading,
  canMutate,
  onDelete,
}) {
  if (loading && (!images || images.length === 0)) {
    return (
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="aspect-square rounded-lg bg-surface-raised animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <EmptyState
        icon={ImageOff}
        title="No dataset images"
        description="Upload images of this student's face to train recognition."
      />
    );
  }

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
      {images.map((img) => (
        <DatasetImageCard
          key={img.filename}
          image={img}
          canMutate={canMutate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
