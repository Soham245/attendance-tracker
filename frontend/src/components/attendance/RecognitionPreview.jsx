import { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, MonitorOff } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';
import { tokenStore } from '../../services/api.js';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const STREAM_URL = `${API_BASE}/preview/stream`;

/**
 * Live MJPEG recognition preview.  Renders the backend's annotated camera
 * feed inside an <img> tag.  The stream is auth-gated; we append the JWT
 * as a query param because <img src> can't send Authorization headers.
 *
 * States:
 *   idle      — session not running, show placeholder
 *   loading   — src set, waiting for first frame
 *   streaming — frames arriving
 *   error     — stream failed or disconnected
 */
export default function RecognitionPreview({ sessionState }) {
  const imgRef = useRef(null);
  const [streamState, setStreamState] = useState('idle'); // idle | loading | streaming | error

  const isRunning = sessionState === 'running';

  const streamUrl = useCallback(() => {
    const token = tokenStore.get();
    const url = new URL(STREAM_URL);
    if (token) url.searchParams.set('token', token);
    return url.toString();
  }, []);

  useEffect(() => {
    if (!isRunning) {
      setStreamState('idle');
      return;
    }

    setStreamState('loading');

    // Small delay so the runtime has time to publish the first frame.
    const timer = setTimeout(() => {
      if (imgRef.current) {
        imgRef.current.src = streamUrl();
      }
    }, 500);

    return () => {
      clearTimeout(timer);
      if (imgRef.current) {
        imgRef.current.src = '';
      }
    };
  }, [isRunning, streamUrl]);

  const handleLoad = () => setStreamState('streaming');
  const handleError = () => {
    if (isRunning) setStreamState('error');
  };

  return (
    <RuntimeCard
      title="Live preview"
      subtitle="Backend camera feed with recognition overlays."
      icon={Camera}
      tone={streamState === 'streaming' ? 'success' : streamState === 'error' ? 'danger' : 'neutral'}
    >
      <div className="relative aspect-video bg-black rounded-md overflow-hidden">
        {isRunning ? (
          <>
            {/* The MJPEG stream rendered as a plain <img> */}
            <img
              ref={imgRef}
              alt="Recognition preview"
              onLoad={handleLoad}
              onError={handleError}
              className={
                'w-full h-full object-contain ' +
                (streamState === 'streaming' ? 'opacity-100' : 'opacity-0')
              }
            />

            {/* Alignment guide overlay */}
            {streamState === 'streaming' ? (
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute inset-[15%] border border-dashed border-white/15 rounded-lg" />
              </div>
            ) : null}

            {/* Loading / error overlays */}
            {streamState === 'loading' ? <Overlay icon={Camera} text="Connecting to camera..." pulse /> : null}
            {streamState === 'error' ? <Overlay icon={MonitorOff} text="Preview disconnected" /> : null}
          </>
        ) : (
          <Overlay icon={CameraOff} text="Start a session to see the live preview" />
        )}
      </div>
    </RuntimeCard>
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
