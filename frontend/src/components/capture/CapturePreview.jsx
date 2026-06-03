import { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, MonitorOff } from 'lucide-react';
import { tokenStore } from '../../services/api.js';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const STREAM_URL = `${API_BASE}/capture/preview/stream`;
const MAX_RETRIES = 6;
const RETRY_DELAY_MS = 1500;

/**
 * MJPEG capture preview — renders the backend's annotated camera feed.
 * Same pattern as RecognitionPreview but for the capture runtime.
 *
 * The backend draws quality overlays, phase instructions, and progress
 * directly onto frames. This component is pure visualization with
 * automatic retry on connection failure (the stream may not be available
 * immediately after the runtime starts).
 */
export default function CapturePreview({ captureState }) {
  const imgRef = useRef(null);
  const [streamState, setStreamState] = useState('idle');
  const retriesRef = useRef(0);
  const retryTimerRef = useRef(null);

  const isCapturing = captureState === 'capturing' || captureState === 'starting';

  const streamUrl = useCallback(() => {
    const token = tokenStore.get();
    const url = new URL(STREAM_URL);
    if (token) url.searchParams.set('token', token);
    // Cache-bust so the browser doesn't serve a stale 204 from cache.
    url.searchParams.set('_t', Date.now().toString());
    return url.toString();
  }, []);

  const connectStream = useCallback(() => {
    if (imgRef.current) {
      imgRef.current.src = streamUrl();
    }
  }, [streamUrl]);

  useEffect(() => {
    if (!isCapturing) {
      setStreamState('idle');
      retriesRef.current = 0;
      clearTimeout(retryTimerRef.current);
      if (imgRef.current) imgRef.current.src = '';
      return;
    }

    setStreamState('loading');
    retriesRef.current = 0;

    // Give the runtime a moment to open the camera and publish the first frame.
    const timer = setTimeout(connectStream, 800);

    return () => {
      clearTimeout(timer);
      clearTimeout(retryTimerRef.current);
      if (imgRef.current) {
        imgRef.current.src = '';
      }
    };
  }, [isCapturing, connectStream]);

  const handleLoad = () => {
    setStreamState('streaming');
    retriesRef.current = 0;
  };

  const handleError = () => {
    if (!isCapturing) return;
    if (retriesRef.current < MAX_RETRIES) {
      retriesRef.current += 1;
      setStreamState('loading');
      retryTimerRef.current = setTimeout(connectStream, RETRY_DELAY_MS);
    } else {
      setStreamState('error');
    }
  };

  return (
    <div className="relative aspect-video bg-black rounded-lg overflow-hidden ring-1 ring-surface-border">
      {isCapturing ? (
        <>
          <img
            ref={imgRef}
            alt="Capture preview"
            onLoad={handleLoad}
            onError={handleError}
            className={
              'w-full h-full object-contain ' +
              (streamState === 'streaming' ? 'opacity-100' : 'opacity-0')
            }
          />

          {streamState === 'loading' ? (
            <Overlay icon={Camera} text="Connecting to camera..." pulse />
          ) : null}
          {streamState === 'error' ? (
            <Overlay icon={MonitorOff} text="Preview disconnected — stop and retry" />
          ) : null}
        </>
      ) : captureState === 'completed' ? (
        <Overlay icon={Camera} text="Enrollment complete" />
      ) : (
        <Overlay icon={CameraOff} text="Press Start to begin guided enrollment" />
      )}
    </div>
  );
}

function Overlay({ icon: Icon, text, pulse }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
      <Icon size={32} className={'text-zinc-600 ' + (pulse ? 'animate-pulse' : '')} />
      <span className="text-xs text-zinc-500">{text}</span>
    </div>
  );
}
