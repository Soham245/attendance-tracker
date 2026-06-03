import { useRef, useState } from 'react';
import { ImagePlus, Upload } from 'lucide-react';
import { cn } from '../../utils/cn.js';

const ACCEPTED = 'image/jpeg,image/png,image/webp';

export default function UploadDropzone({ onFiles, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const pick = () => inputRef.current?.click();

  const handleFiles = (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList).filter((f) => f.type.startsWith('image/'));
    if (files.length === 0) return;
    onFiles(files);
  };

  return (
    <div
      onDragOver={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={disabled ? undefined : pick}
      className={cn(
        'rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors',
        'cursor-pointer select-none',
        dragging
          ? 'border-accent/60 bg-accent/5'
          : 'border-surface-border bg-surface-raised/40 hover:bg-surface-hover/40',
        disabled && 'opacity-60 cursor-not-allowed',
      )}
    >
      <div className="flex flex-col items-center gap-2">
        <div className="grid place-items-center h-10 w-10 rounded-full bg-accent/15 text-accent">
          {dragging ? <Upload size={18} /> : <ImagePlus size={18} />}
        </div>
        <div className="text-sm text-zinc-200">
          {dragging ? 'Drop to upload' : 'Click or drop images here'}
        </div>
        <div className="text-[11px] text-zinc-500">
          JPG, PNG, or WebP. Multiple files supported.
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
      />
    </div>
  );
}
