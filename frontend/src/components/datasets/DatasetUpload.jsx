import { useState } from 'react';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import UploadDropzone from './UploadDropzone.jsx';
import { uploadDatasetImage } from '../../services/datasetService.js';
import { errorMessage } from '../../services/api.js';

/**
 * Sequentially uploads queued files, surfacing per-file status. Sequential rather
 * than parallel because the backend writes them to disk one at a time anyway and
 * concurrent uploads make failure recovery harder for the user to reason about.
 */
export default function DatasetUpload({ studentId, disabled, onUploaded }) {
  const [items, setItems] = useState([]); // [{ id, file, status, progress, error }]
  const [busy, setBusy] = useState(false);

  const enqueue = async (files) => {
    const queued = files.map((file, i) => ({
      id: `${Date.now()}-${i}-${file.name}`,
      file,
      status: 'pending',
      progress: 0,
      error: null,
    }));
    setItems((prev) => [...queued, ...prev].slice(0, 24));
    setBusy(true);

    let any = false;
    for (const item of queued) {
      // eslint-disable-next-line no-await-in-loop
      await uploadOne(item);
      any = true;
    }
    setBusy(false);
    if (any) onUploaded?.();
  };

  const uploadOne = async (item) => {
    setItems((prev) =>
      prev.map((p) => (p.id === item.id ? { ...p, status: 'uploading' } : p)),
    );
    try {
      await uploadDatasetImage(studentId, item.file, {
        onProgress: (pct) =>
          setItems((prev) =>
            prev.map((p) => (p.id === item.id ? { ...p, progress: pct } : p)),
          ),
      });
      setItems((prev) =>
        prev.map((p) =>
          p.id === item.id ? { ...p, status: 'done', progress: 100 } : p,
        ),
      );
    } catch (err) {
      setItems((prev) =>
        prev.map((p) =>
          p.id === item.id
            ? { ...p, status: 'failed', error: errorMessage(err, 'Upload failed') }
            : p,
        ),
      );
    }
  };

  const retry = (item) => {
    uploadOne(item).finally(() => onUploaded?.());
  };

  return (
    <div className="space-y-3">
      <UploadDropzone onFiles={enqueue} disabled={disabled || busy} />

      {items.length > 0 ? (
        <ul className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center gap-3 rounded-md bg-surface-raised/60 border border-surface-border px-3 py-2"
            >
              <StatusIcon status={item.status} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs text-zinc-200">
                  {item.file.name}
                </div>
                {item.status === 'uploading' ? (
                  <div className="mt-1 h-1 rounded-full bg-surface-border overflow-hidden">
                    <div
                      className="h-full bg-accent transition-[width]"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                ) : item.status === 'failed' ? (
                  <div className="mt-0.5 text-[11px] text-rose-300">
                    {item.error}
                  </div>
                ) : null}
              </div>
              {item.status === 'failed' ? (
                <button
                  type="button"
                  onClick={() => retry(item)}
                  className="text-[11px] text-accent hover:text-accent-hover"
                >
                  Retry
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function StatusIcon({ status }) {
  if (status === 'uploading' || status === 'pending') {
    return <Loader2 size={14} className="animate-spin text-zinc-400 shrink-0" />;
  }
  if (status === 'done') {
    return <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />;
  }
  if (status === 'failed') {
    return <XCircle size={14} className="text-rose-400 shrink-0" />;
  }
  return null;
}
