'use client';

import { createPortal } from 'react-dom';

import Draggable from 'react-draggable';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useGlobalPlayer } from './GlobalPlayerContext';
import { useAuth } from '@/lib/auth';
import { coursesApi, progressApi } from '@/lib/api';
import { formatDuration } from '@/lib/utils';
import { usePathname, useRouter } from 'next/navigation';

export default function GlobalPlayer() {
  const { videoId, isPiP, setIsPiP, setVideoId, mountNode, video, setVideo } = useGlobalPlayer();
  const { token } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const nodeRef = useRef<HTMLDivElement>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    if (!isPiP) setIsCollapsed(false);
  }, [isPiP]);

  // Auto-PiP when navigating away from /player
  const prevPathname = useRef(pathname);
  useEffect(() => {
    if (prevPathname.current === '/player' && pathname !== '/player' && video) {
      setIsPiP(true);
    }
    prevPathname.current = pathname;
  }, [pathname, video, setIsPiP]);

  useEffect(() => {
    if (!videoId || !token) {
      setVideo(null);
      return;
    }
    coursesApi.getVideo(token, videoId).then(setVideo).catch((err: any) => {
      console.error(err);
      if (err.status === 404) {
        setVideoId(0);
        localStorage.removeItem('current_video_id');
      }
    });
  }, [videoId, token, setVideoId]);

  if (!video) return null;
  if (!mounted) return null;

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const lastPosition = video.progress?.last_position || 0;
  const isYoutube = !!video.youtube_id;
  const isBrokenYoutube = video.mime_type === 'video/youtube' && !video.youtube_id;

  // If we are on /player and isPiP is false, we don't render the global floating player,
  // we render it inline! Wait, to render it inline on /player, we can just use CSS classes.
  // Actually, if we are on /player, the player page will just render an empty div of height 500px, 
  // and this GlobalPlayer will use position: absolute or fixed based on PiP state.


  const content = (
    <div ref={nodeRef} className={isPiP ? "pip-container" : ""} style={!isPiP ? { width: '100%', height: '100%' } : {}}>
       {isPiP && (
         <div className="player-drag-handle" style={{
           padding: '12px 16px',
           background: 'var(--surface-light)',
           borderBottom: '1px solid rgba(255,255,255,0.05)',
           display: 'flex',
           justifyContent: 'space-between',
           alignItems: 'center',
           cursor: 'grab'
         }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>
              {isCollapsed ? "Video Playing" : "Now Playing"}
            </div>
            <div className="nodrag" style={{ display: 'flex', gap: 8 }}>
               <button onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }} className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}>
                 {isCollapsed ? "Expand" : "Collapse"}
               </button>
               {!isCollapsed && (
                 <button onClick={(e) => { e.stopPropagation(); setIsPiP(false); router.push('/player'); }} className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}>
                   Fullscreen
                 </button>
               )}
               <button onClick={(e) => { e.stopPropagation(); setVideo(null); }} className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}>
                 Close
               </button>
            </div>
         </div>
       )}
       
       <div className="nodrag" style={{ 
         background: '#000', 
         borderRadius: isPiP ? 0 : 16, 
         overflow: 'hidden', 
         position: isCollapsed ? 'absolute' : 'relative',
         left: isCollapsed ? -9999 : 'auto',
         width: isCollapsed ? 350 : '100%',
         height: 'auto',
         opacity: isCollapsed ? 0 : 1
       }}>
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

  const targetNode = (!isPiP && pathname === '/player' && mountNode) ? mountNode : document.body;
  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;

  // By using createPortal consistently, React moves the DOM node instead of remounting it,
  // preventing iframe reloads when toggling between PiP and inline mode.
  return createPortal(
    <Draggable 
      handle=".player-drag-handle" 
      cancel=".nodrag" 
      nodeRef={nodeRef}
      disabled={!isPiP || isMobile}
      position={!isPiP ? {x: 0, y: 0} : undefined}
    >
      {content}
    </Draggable>,
    targetNode
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
      playsInline
      style={{ width: '100%', display: 'block', maxHeight: '70vh' }}
    >
      <source src={`${apiBase}/api/stream/${videoMsgId}`} type="video/mp4" />
    </video>
  );
}
