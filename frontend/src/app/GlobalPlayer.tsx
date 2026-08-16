'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useGlobalPlayer } from './GlobalPlayerContext';
import { useAuth } from '@/lib/auth';
import { coursesApi, progressApi } from '@/lib/api';
import { formatDuration } from '@/lib/utils';
import { usePathname } from 'next/navigation';

export default function GlobalPlayer() {
  const { videoId, isPiP, setIsPiP, setVideoId } = useGlobalPlayer();
  const { token } = useAuth();
  const [video, setVideo] = useState<any>(null);
  const pathname = usePathname();

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!videoId || !token) {
      setVideo(null);
      return;
    }
    coursesApi.getVideo(token, videoId).then(setVideo).catch(console.error);
  }, [videoId, token]);

  if (!video) return null;

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const lastPosition = video.progress?.last_position || 0;
  const isYoutube = !!video.youtube_id;
  const isBrokenYoutube = video.mime_type === 'video/youtube' && !video.youtube_id;

  // If we are on /player and isPiP is false, we don't render the global floating player,
  // we render it inline! Wait, to render it inline on /player, we can just use CSS classes.
  // Actually, if we are on /player, the player page will just render an empty div of height 500px, 
  // and this GlobalPlayer will use position: absolute or fixed based on PiP state.


  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: 24,
    right: 24,
    width: 350,
    zIndex: 9999,
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
    background: '#0E1117',
    border: '1px solid rgba(255,255,255,0.1)',
    transition: 'all 0.3s ease',
  };

  if (!mounted) return null;

  return (
    <div style={containerStyle}>
       <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 16px', background: '#1A1D29', fontSize: 13, fontWeight: 600 }}>
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '80%' }}>{video.title}</span>
          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ cursor: 'pointer', color: '#ff4d4f' }} onClick={() => setVideoId(0)} title="Close">✕</span>
          </div>
       </div>
       
       <div style={{ background: '#000', overflow: 'hidden' }}>
         {isYoutube ? (
            <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
              <iframe
                src={`https://www.youtube.com/embed/${video.youtube_id}?start=${Math.floor(lastPosition)}`}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
         ) : isBrokenYoutube ? (
            <div style={{ padding: 16, color: 'red', fontSize: 12 }}>Broken YT Video</div>
         ) : (
            <TelegramPlayer 
              videoMsgId={video.telegram_msg_id} 
              videoId={video.id} 
              token={token} 
              apiBase={apiBase} 
              lastPosition={lastPosition} 
            />
         )}
       </div>
    </div>
  );
}

function TelegramPlayer({ videoMsgId, videoId, token, apiBase, lastPosition }: any) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [totalWatched, setTotalWatched] = useState(0);
  const lastSavedRef = useRef(0);

  const saveProgress = useCallback((watchSec: number, pos: number) => {
    progressApi.update(token, videoId, watchSec, pos).catch(() => {});
  }, [token, videoId]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onLoaded = () => { if (lastPosition > 0) video.currentTime = lastPosition; };
    const onTimeUpdate = () => {
      const current = Math.floor(video.currentTime);
      setTotalWatched(prev => {
        const newVal = Math.max(prev, current);
        if (current - lastSavedRef.current >= 10) {
          lastSavedRef.current = current;
          saveProgress(newVal, current);
        }
        return newVal;
      });
    };
    const onEnded = () => {
      saveProgress(totalWatched, video.duration);
      progressApi.complete(token, videoId).catch(() => {});
    };
    const onPause = () => saveProgress(totalWatched, Math.floor(video.currentTime));

    video.addEventListener('loadedmetadata', onLoaded);
    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('ended', onEnded);
    video.addEventListener('pause', onPause);
    return () => {
      video.removeEventListener('loadedmetadata', onLoaded);
      video.removeEventListener('timeupdate', onTimeUpdate);
      video.removeEventListener('ended', onEnded);
      video.removeEventListener('pause', onPause);
    };
  }, [lastPosition, saveProgress, token, videoId, totalWatched]);

  return (
    <video
      ref={videoRef}
      controls
      controlsList="nodownload"
      style={{ width: '100%', display: 'block', maxHeight: '70vh' }}
    >
      <source src={`${apiBase}/api/stream/${videoMsgId}`} type="video/mp4" />
    </video>
  );
}
