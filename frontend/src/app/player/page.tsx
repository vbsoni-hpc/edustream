'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { coursesApi, progressApi, aiApi, usersApi } from '@/lib/api';
import { useGlobalPlayer } from '../GlobalPlayerContext';
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
  const { videoId: globalVideoId, setVideoId, setIsPiP } = useGlobalPlayer();

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
    setVideoId(id);
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

      {/* Floating Player Indicator */}
      <div style={{ 
        minHeight: '30vh', marginBottom: 24, borderRadius: 16, 
        background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12
      }}>
        <div style={{ fontSize: 40 }}>🎥</div>
        <div style={{ color: 'var(--text-secondary)' }}>Video is playing in the floating player</div>
      </div>
{/* Watching Now */}
      <WatchingNow videoId={video.id} token={token!} />

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

/* ── Watching Now Section ────────────────────────────────── */
function WatchingNow({ videoId, token }: { videoId: number; token: string }) {
  const [watchers, setWatchers] = useState<any[]>([]);

  const fetchWatchers = useCallback(async () => {
    try {
      // Ping that we are watching
      await usersApi.ping(token, videoId);
      // Fetch who else is watching
      const res = await usersApi.getWatching(videoId);
      setWatchers(res.users || []);
    } catch (e) {
      console.error(e);
    }
  }, [videoId, token]);

  useEffect(() => {
    fetchWatchers();
    const interval = setInterval(fetchWatchers, 15000); // 15s refresh
    return () => clearInterval(interval);
  }, [fetchWatchers]);

  if (watchers.length === 0) return null;

  return (
    <div style={{
      marginTop: 24, padding: 16, background: 'rgba(255,255,255,0.02)',
      borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)',
      display: 'flex', alignItems: 'center', gap: 16, overflowX: 'auto'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, color: 'var(--text-secondary)', fontSize: 14 }}>
        <span className="online-dot" style={{ width: 10, height: 10, margin: 0 }} />
        Watching Now ({watchers.length})
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {watchers.map((w, i) => (
          <div 
            key={i} 
            onClick={() => window.dispatchEvent(new CustomEvent('open-dm', { detail: { id: w.id, name: w.display_name } }))}
            style={{
              background: 'var(--bg-card)', padding: '6px 12px', borderRadius: 20,
              fontSize: 13, border: '1px solid rgba(255,255,255,0.1)',
              display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer'
            }}
            title={`DM ${w.display_name}`}
          >
            <span style={{ fontSize: 16 }}>{w.is_admin ? '👑' : '👤'}</span>
            {w.display_name}
          </div>
        ))}
      </div>
    </div>
  );
}
