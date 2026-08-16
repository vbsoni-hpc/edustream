'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { coursesApi, subscriptionsApi } from '@/lib/api';
import { formatDuration, naturalCompare } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import { useRouter } from 'next/navigation';

export default function CoursesPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <CoursesContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function CoursesContent() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [segments, setSegments] = useState<any[]>([]);
  const [subscribedIds, setSubscribedIds] = useState<number[]>([]);
  const [selectedSegment, setSelectedSegment] = useState<string>('all');
  const [sortMode, setSortMode] = useState<string>('lecture');
  const [expandedSeg, setExpandedSeg] = useState<number | null>(null);
  const [segVideos, setSegVideos] = useState<Record<number, any[]>>({});
  const [segModules, setSegModules] = useState<Record<number, any[]>>({});
  const [segLeaderboard, setSegLeaderboard] = useState<Record<number, any[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const [segRes, subsRes] = await Promise.all([
          coursesApi.getSegments(token),
          subscriptionsApi.get(token),
        ]);
        setSegments(segRes.segments);
        setSubscribedIds(subsRes.subscribed_ids);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  const mySegments = segments.filter(s => subscribedIds.includes(s.id));

  const filteredSegments = selectedSegment === 'all'
    ? mySegments
    : mySegments.filter(s => s.id === parseInt(selectedSegment));

  const toggleSegment = async (segId: number) => {
    if (expandedSeg === segId) {
      setExpandedSeg(null);
      return;
    }
    setExpandedSeg(segId);
    if (!segVideos[segId] && token) {
      try {
        const [vidRes, modRes, lbRes] = await Promise.all([
          coursesApi.getSegmentVideos(token, segId),
          coursesApi.getSegmentModules(token, segId),
          coursesApi.getSegmentLeaderboard(segId),
        ]);
        setSegVideos(prev => ({ ...prev, [segId]: vidRes.videos }));
        setSegModules(prev => ({ ...prev, [segId]: modRes.modules }));
        setSegLeaderboard(prev => ({ ...prev, [segId]: lbRes.leaderboard }));
      } catch (err) {
        console.error(err);
      }
    }
  };

  const sortVideos = (videos: any[]): any[] => {
    const sorted = [...videos];
    switch (sortMode) {
      case 'lecture': return sorted.sort((a, b) => naturalCompare(a.title, b.title));
      case 'az': return sorted.sort((a, b) => a.title.localeCompare(b.title));
      case 'za': return sorted.sort((a, b) => b.title.localeCompare(a.title));
      case 'short': return sorted.sort((a, b) => a.duration_sec - b.duration_sec);
      case 'long': return sorted.sort((a, b) => b.duration_sec - a.duration_sec);
      default: return sorted;
    }
  };

  const playVideo = (videoId: number) => {
    localStorage.setItem('current_video_id', String(videoId));
    router.push('/player');
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading courses...</span></div>;
  }

  if (mySegments.length === 0) {
    return (
      <div className="empty-state" style={{ marginTop: 60 }}>
        <div className="empty-state-icon">📚</div>
        <p className="empty-state-text">
          You haven&#39;t subscribed to any courses yet.<br />
          Go to the <a href="/" style={{ color: 'var(--primary-light)' }}>Dashboard</a> to discover and subscribe to courses!
        </p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 24 }}>📚 My Courses</h1>

      {/* Filters */}
      <div className="flex-row mb-6" style={{ gap: 12 }}>
        <select className="select" style={{ maxWidth: 240 }} value={selectedSegment} onChange={(e) => setSelectedSegment(e.target.value)}>
          <option value="all">All Segments</option>
          {mySegments.map(s => (
            <option key={s.id} value={s.id}>{s.icon} {s.name}</option>
          ))}
        </select>
        <select className="select" style={{ maxWidth: 220 }} value={sortMode} onChange={(e) => setSortMode(e.target.value)}>
          <option value="lecture">Lecture Number</option>
          <option value="az">Title (A-Z)</option>
          <option value="za">Title (Z-A)</option>
          <option value="short">Duration (Short→Long)</option>
          <option value="long">Duration (Long→Short)</option>
        </select>
      </div>

      {/* Segment Expanders */}
      {filteredSegments.map(seg => {
        const videos = segVideos[seg.id] || [];
        const sortedVideos = sortVideos(videos);
        const completedCount = sortedVideos.filter(v => v.progress?.completed).length;
        const pct = sortedVideos.length > 0 ? (completedCount / sortedVideos.length * 100) : 0;
        const isOpen = expandedSeg === seg.id;
        const modules = segModules[seg.id] || [];
        const leaderboard = segLeaderboard[seg.id] || [];

        return (
          <div key={seg.id} className="expander">
            <div className="expander-header" onClick={() => toggleSegment(seg.id)}>
              <span>
                {seg.icon} {seg.name} — {completedCount}/{sortedVideos.length} completed · {pct.toFixed(0)}% done
                {seg.uploaded_by_username && <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--primary-light)' }}>(Shared by @{seg.uploaded_by_username})</span>}
              </span>
              <span className={`expander-chevron ${isOpen ? 'open' : ''}`}>▼</span>
            </div>
            {isOpen && (
              <div className="expander-content">
                <div className="progress-outer" style={{ marginBottom: 16 }}>
                  <div className="progress-inner" style={{ width: `${pct}%` }} />
                </div>

                {/* Leaderboard */}
                {leaderboard.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <h5 style={{ color: 'var(--text-primary)', marginBottom: 8 }}>🏆 Course Leaderboard (Last 7 Days)</h5>
                    <div className="flex-row flex-wrap">
                      {leaderboard.slice(0, 3).map((u: any, i: number) => {
                        const medals = ['🥇', '🥈', '🥉'];
                        return (
                          <span key={i} style={{ fontSize: 14, fontWeight: 600 }}>
                            {medals[i]} {u.display_name} — {(u.total_watch_sec / 3600).toFixed(1)}h
                          </span>
                        );
                      })}
                    </div>
                    <div className="divider" />
                  </div>
                )}

                {/* Videos */}
                {modules.length > 0 ? (
                  <>
                    {modules.map((mod: any) => {
                      const modVideos = sortedVideos.filter(v => v.module_id === mod.id);
                      if (modVideos.length === 0) return null;
                      const modDone = modVideos.filter(v => v.progress?.completed).length;
                      const modPct = (modDone / modVideos.length * 100).toFixed(0);
                      return (
                        <ModuleSection
                          key={mod.id}
                          mod={mod}
                          videos={modVideos}
                          donePct={modPct}
                          doneCount={modDone}
                          onPlay={playVideo}
                        />
                      );
                    })}
                    {/* Unassigned */}
                    {(() => {
                      const unassigned = sortedVideos.filter(v => !v.module_id);
                      if (unassigned.length === 0) return null;
                      return (
                        <div style={{ marginTop: 12 }}>
                          <h5 style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>📄 Other Lectures — {unassigned.length} videos</h5>
                          <VideoList videos={unassigned} onPlay={playVideo} />
                        </div>
                      );
                    })()}
                  </>
                ) : (
                  <VideoList videos={sortedVideos} onPlay={playVideo} />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ModuleSection({ mod, videos, donePct, doneCount, onPlay }: {
  mod: any; videos: any[]; donePct: string; doneCount: number; onPlay: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          cursor: 'pointer', padding: '10px 0', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', fontSize: 14, fontWeight: 600, color: 'var(--text-primary)',
        }}
      >
        <span>{mod.icon} {mod.name} — {doneCount}/{videos.length} done · {donePct}%</span>
        <span style={{ color: 'var(--text-muted)', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}>▼</span>
      </div>
      {open && <VideoList videos={videos} onPlay={onPlay} />}
    </div>
  );
}

function VideoList({ videos, onPlay }: { videos: any[]; onPlay: (id: number) => void }) {
  return (
    <div style={{ maxHeight: 400, overflowY: 'auto' }}>
      {videos.map((video, idx) => {
        const isComplete = video.progress?.completed;
        const watchSec = video.progress?.watch_seconds || 0;
        return (
          <div key={video.id} className="video-card" onClick={() => onPlay(video.id)}>
            <div className="video-left">
              <div className={`video-index ${isComplete ? 'completed' : ''}`}>
                {isComplete ? '✓' : idx + 1}
              </div>
              <div style={{ minWidth: 0 }}>
                <div className="video-title">{video.title}</div>
                <div className="video-meta">Duration: {formatDuration(video.duration_sec)}</div>
              </div>
            </div>
            <div className="video-right">
              <span className={`watch-badge ${isComplete ? 'done' : ''}`}>
                {isComplete ? '✅ Done' : `▶ ${formatDuration(watchSec)} watched`}
              </span>
              <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); onPlay(video.id); }}>
                ▶️ Play
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
