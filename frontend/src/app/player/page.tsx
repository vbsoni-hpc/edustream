'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { coursesApi, progressApi, aiApi } from '@/lib/api';
import { formatDuration, naturalCompare } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';

export default function PlayerPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <PlayerContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function PlayerContent() {
  const { token, user } = useAuth();
  const [video, setVideo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isComplete, setIsComplete] = useState(false);
  const [siblingVideos, setSiblingVideos] = useState<any[]>([]);
  const [currentIdx, setCurrentIdx] = useState(-1);

  const videoId = typeof window !== 'undefined' ? parseInt(localStorage.getItem('current_video_id') || '0') : 0;

  const loadVideo = useCallback(async (id: number) => {
    if (!token || !id) return;
    setLoading(true);
    try {
      const v = await coursesApi.getVideo(token, id);
      setVideo(v);
      setIsComplete(v.progress?.completed || false);

      // Load siblings for nav
      if (v.segment_id) {
        const segRes = await coursesApi.getSegmentVideos(token, v.segment_id);
        const sorted = segRes.videos.sort((a: any, b: any) => naturalCompare(a.title, b.title));
        setSiblingVideos(sorted);
        setCurrentIdx(sorted.findIndex((sv: any) => sv.id === id));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { if (videoId) loadVideo(videoId); }, [videoId, loadVideo]);

  const navigateTo = (id: number) => {
    localStorage.setItem('current_video_id', String(id));
    loadVideo(id);
  };

  const handleMarkComplete = async () => {
    if (!token || !video) return;
    await progressApi.complete(token, video.id);
    setIsComplete(true);
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading player...</span></div>;
  }

  if (!video) {
    return (
      <div className="empty-state" style={{ marginTop: 60 }}>
        <div className="empty-state-icon">🎬</div>
        <p className="empty-state-text">
          No video selected. Go to <a href="/courses" style={{ color: 'var(--primary-light)' }}>My Courses</a> and pick a video to watch.
        </p>
      </div>
    );
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
  const lastPosition = video.progress?.last_position || 0;
  const isYoutube = !!video.youtube_id;
  const isBrokenYoutube = video.mime_type === 'video/youtube' && !video.youtube_id;

  const prevVideo = currentIdx > 0 ? siblingVideos[currentIdx - 1] : null;
  const nextVideo = currentIdx >= 0 && currentIdx < siblingVideos.length - 1 ? siblingVideos[currentIdx + 1] : null;

  return (
    <div className="animate-fade-in">
      {/* Breadcrumb */}
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
        <span style={{ color: 'var(--primary-light)', fontWeight: 600 }}>
          {video.segment_icon || '📁'} {video.segment_name || 'Uncategorized'}
        </span>
      </div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>{video.title}</h1>

      {isComplete && (
        <div className="form-success" style={{ marginBottom: 16 }}>✅ You&#39;ve completed this video!</div>
      )}

      {/* Video Player */}
      {isYoutube ? (
        <div style={{ marginBottom: 24 }}>
          <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, borderRadius: 16, overflow: 'hidden' }}>
            <iframe
              src={`https://www.youtube.com/embed/${video.youtube_id}?start=${Math.floor(lastPosition)}`}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          <p style={{ marginTop: 8, fontSize: 14, color: 'var(--text-secondary)' }}>
            🔗 <a href={`https://www.youtube.com/watch?v=${video.youtube_id}`} target="_blank" rel="noreferrer"
                  style={{ color: 'var(--primary-light)' }}>Watch directly on YouTube ↗</a>
          </p>
          <div className="notice-banner" style={{ marginTop: 8 }}>
            ℹ️ Progress tracking is limited for YouTube videos. Please use the Mark as Complete button below when finished.
          </div>
        </div>
      ) : isBrokenYoutube ? (
        <div className="form-error" style={{ marginBottom: 24 }}>
          This YouTube video is missing its video ID and cannot be played. Please contact the administrator.
        </div>
      ) : (
        <TelegramPlayer
          videoMsgId={video.telegram_msg_id}
          videoId={video.id}
          token={token!}
          apiBase={apiBase}
          lastPosition={lastPosition}
          onComplete={() => setIsComplete(true)}
        />
      )}

      {/* AI Chat */}
      <AIChatSection videoId={video.id} videoTitle={video.title} />

      {/* Mark Complete */}
      <div style={{ marginTop: 24 }}>
        {!isComplete ? (
          <button className="btn btn-primary" onClick={handleMarkComplete}>
            ✅ Mark as Complete
          </button>
        ) : (
          <span style={{ fontSize: 15, fontWeight: 600 }}>✅ Completed</span>
        )}
      </div>

      {/* Prev / Next Nav */}
      <div className="grid-2 mt-8">
        {prevVideo ? (
          <div className="glass-card" onClick={() => navigateTo(prevVideo.id)} style={{ cursor: 'pointer' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>← Previous</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{prevVideo.title}</div>
          </div>
        ) : <div />}
        {nextVideo ? (
          <div className="glass-card" onClick={() => navigateTo(nextVideo.id)} style={{ cursor: 'pointer' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Next →</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{nextVideo.title}</div>
          </div>
        ) : <div />}
      </div>
    </div>
  );
}

/* ── Telegram Video Player ──────────────────────────────── */
function TelegramPlayer({ videoMsgId, videoId, token, apiBase, lastPosition, onComplete }: {
  videoMsgId: number; videoId: number; token: string; apiBase: string; lastPosition: number; onComplete: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [totalWatched, setTotalWatched] = useState(0);
  const lastSavedRef = useRef(0);
  const [error, setError] = useState(false);

  const saveProgress = useCallback((watchSec: number, pos: number) => {
    progressApi.update(token, videoId, watchSec, pos).catch(() => {});
  }, [token, videoId]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onLoaded = () => {
      if (lastPosition > 0) video.currentTime = lastPosition;
    };

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
      progressApi.complete(token, videoId).then(onComplete).catch(() => {});
    };

    const onPause = () => {
      saveProgress(totalWatched, Math.floor(video.currentTime));
    };

    const onError = () => setError(true);

    video.addEventListener('loadedmetadata', onLoaded);
    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('ended', onEnded);
    video.addEventListener('pause', onPause);
    video.addEventListener('error', onError);

    return () => {
      video.removeEventListener('loadedmetadata', onLoaded);
      video.removeEventListener('timeupdate', onTimeUpdate);
      video.removeEventListener('ended', onEnded);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('error', onError);
    };
  }, [lastPosition, saveProgress, token, videoId, onComplete, totalWatched]);

  if (error) {
    return (
      <div className="glass-card-static" style={{ textAlign: 'center', padding: '48px 24px', marginBottom: 24 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h3 style={{ marginBottom: 8 }}>Video Failed to Load</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>The streaming server may not be running.</p>
        <button className="btn btn-primary" onClick={() => { setError(false); }}>🔄 Retry</button>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ borderRadius: 16, overflow: 'hidden', boxShadow: '0 8px 32px rgba(108, 99, 255, 0.15)', background: '#0E1117' }}>
        <video
          ref={videoRef}
          controls
          preload="metadata"
          style={{ width: '100%', display: 'block', maxHeight: '70vh' }}
        >
          <source src={`${apiBase}/api/stream/${videoMsgId}`} type="video/mp4" />
        </video>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 16px', background: '#1A1D29', fontSize: 13, color: 'var(--text-secondary)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className="online-dot" style={{ width: 8, height: 8, marginRight: 0, background: 'var(--primary)' }} />
            Streaming from Telegram
          </div>
          <span>{formatDuration(totalWatched)} watched</span>
        </div>
      </div>
    </div>
  );
}

/* ── AI Chat Section ────────────────────────────────────── */
function AIChatSection({ videoId, videoTitle }: { videoId: number; videoTitle: string }) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !token) return;

    const userMsg = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await aiApi.chat(token, [...messages, userMsg], videoTitle);
      setMessages(prev => [...prev, { role: 'assistant', content: res.response }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card-static mt-6">
      <h5 style={{ color: 'var(--text-primary)', marginBottom: 12 }}>🤖 Ask AI Tutor</h5>
      <div style={{ maxHeight: 300, overflowY: 'auto', marginBottom: 12 }}>
        {messages.length === 0 && (
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Got a question about this lecture? Ask the AI!</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 8, fontSize: 14, lineHeight: 1.6 }}>
            {msg.role === 'user' ? (
              <span><strong>👤 You:</strong> {msg.content}</span>
            ) : (
              <span><strong>🤖 AI:</strong> {msg.content}</span>
            )}
          </div>
        ))}
        {loading && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>AI is thinking...</p>}
      </div>
      <form onSubmit={handleAsk} style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Summarize this video's topic"
          disabled={loading}
        />
        <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
          Ask 🚀
        </button>
      </form>
    </div>
  );
}
