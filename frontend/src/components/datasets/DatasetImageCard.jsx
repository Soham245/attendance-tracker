import { Image as ImageIcon, Trash2 } from 'lucide-react';

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Backend currently exposes dataset images by metadata only (filename + size).
 * We render a metadata card with a generic icon — when an image-byte endpoint
 * lands, swap the icon block for a real <img>.
 */
export default function DatasetImageCard({ image, onDelete, canMutate }) {
  return (
    <div className="group relative overflow-hidden rounded-lg border border-surface-border bg-surface-raised">
      <div className="aspect-square w-full bg-surface grid place-items-center">
        <ImageIcon size={26} className="text-zinc-600" />
      </div>

      <div className="px-2.5 py-2 border-t border-surface-border">
        <div className="truncate text-[11px] text-zinc-300" title={image.filename}>
          {image.filename}
        </div>
        <div className="text-[10px] text-zinc-500 tabular-nums">
          {formatSize(image.size_bytes)}
        </div>
      </div>

      {canMutate ? (
        <button
          type="button"
          onClick={() => onDelete(image)}
          className="absolute right-1.5 top-1.5 grid place-items-center h-7 w-7 rounded-md bg-black/60 text-zinc-200 opacity-0 group-hover:opacity-100 hover:bg-rose-600/80 transition"
          title="Delete image"
        >
          <Trash2 size={13} />
        </button>
      ) : null}
    </div>
  );
}
