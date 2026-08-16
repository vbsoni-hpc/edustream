'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { dashboardApi, subscriptionsApi, importApi } from '@/lib/api';
import { formatHours } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import Link from 'next/link';

export default function HomePage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Dashboard />
        </main>
      </div>
    </AuthGuard>
  );
}

function Dashboard() {
  const { user, token } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [lastSeg, setLastSeg] = useState<any>(null);
  const [segStats, setSegStats] = useState<any[]>([]);
  const [subscribedIds, setSubscribedIds] = useState<Set<number>>(new Set());
  const [dailyLb, setDailyLb] = useState<any[]>([]);
  const [weeklyLb, setWeeklyLb] = useState<any[]>([]);
  const [notices, setNotices] = useState<any[]>([]);
  const [showImport, setShowImport] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    if (!token) return;
    try {
      const [statsRes, lastRes, segRes, subsRes, dailyRes, weeklyRes, noticeRes] = await Promise.all([
        dashboardApi.getStats(token),
        dashboardApi.getLastSegment(token),
        dashboardApi.getSegmentStats(token),
        subscriptionsApi.get(token),
        dashboardApi.getLeaderboard(token, 1),
        dashboardApi.getLeaderboard(token, 7),
        dashboardApi.getNotices(),
      ]);
      setStats(statsRes);
      setLastSeg(lastRes.segment);
      setSegStats(segRes.segments.filter((s: any) => s.name !== 'General' && s.name !== 'Uncategorized'));
      setSubscribedIds(new Set(subsRes.subscribed_ids));
      setDailyLb(dailyRes.leaderboard);
      setWeeklyLb(weeklyRes.leaderboard);
      setNotices(noticeRes.notices);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

  const handleSubscribe = async (segId: number) => {
    if (!token) return;
    await subscriptionsApi.subscribe(token, segId);
    setSubscribedIds(prev => new Set([...prev, segId]));
  };

  const handleUnsubscribe = async (segId: number) => {
    if (!token) return;
    await subscriptionsApi.unsubscribe(token, segId);
    setSubscribedIds(prev => { const s = new Set(prev); s.delete(segId); return s; });
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading dashboard...</span></div>;
  }

  const myCourses = segStats.filter(s => subscribedIds.has(s.id));

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <div className="flex-between mb-6">
        <div>
          <h1 className="hero-title">Welcome back, {user?.display_name} 👋</h1>
          <p className="hero-subtitle">Continue your learning journey</p>
        </div>
        <button className="btn btn-secondary" onClick={() => setShowImport(true)}>
          ➕ Upload a Course
        </button>
      </div>

      {/* Notices */}
      {notices.length > 0 && (
        <div className="mb-6">
          <h4 className="section-title">📢 Important Notices</h4>
          {notices.map((n: any) => (
            <div key={n.id} className="notice-banner">{n.content}</div>
          ))}
        </div>
      )}

      {/* Last viewed segment progress */}
      {lastSeg && (
        <div className="glass-card-static mb-6">
          <div className="flex-between" style={{ marginBottom: 12 }}>
            <span style={{ fontWeight: 600 }}>
              Last Viewed Course: {lastSeg.icon} {lastSeg.name}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              {lastSeg.completed_videos}/{lastSeg.total_videos} videos · {formatHours(lastSeg.watch_seconds)} watched
            </span>
          </div>
          <div className="progress-outer">
            <div
              className="progress-inner"
              style={{ width: `${lastSeg.total_videos > 0 ? (lastSeg.completed_videos / lastSeg.total_videos * 100) : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* My Courses Carousel */}
      <h4 className="section-title">📚 My Courses</h4>
      {myCourses.length === 0 ? (
        <div className="empty-state" style={{ padding: '24px' }}>
          <p className="empty-state-text">No courses subscribed yet. Browse All Courses below and subscribe!</p>
        </div>
      ) : (
        <div className="carousel mb-6">
          {myCourses.map(seg => (
            <CourseCard
              key={seg.id}
              seg={seg}
              subscribed={true}
              onSubscribe={handleSubscribe}
              onUnsubscribe={handleUnsubscribe}
            />
          ))}
        </div>
      )}

      {/* All Courses Carousel */}
      <h4 className="section-title" style={{ marginTop: 32 }}>🌐 All Courses</h4>
      {segStats.length === 0 ? (
        <div className="empty-state" style={{ padding: '24px' }}>
          <p className="empty-state-text">No courses available yet.</p>
        </div>
      ) : (
        <div className="carousel mb-6">
          {segStats.map(seg => (
            <CourseCard
              key={seg.id}
              seg={seg}
              subscribed={subscribedIds.has(seg.id)}
              onSubscribe={handleSubscribe}
              onUnsubscribe={handleUnsubscribe}
            />
          ))}
        </div>
      )}

      {/* Leaderboards */}
      <h4 className="section-title" style={{ marginTop: 32 }}>🏆 Top Learners</h4>
      <div className="grid-2">
        <LeaderboardCard title="Daily Watch Hours" data={dailyLb} />
        <LeaderboardCard title="Weekly Watch Hours" data={weeklyLb} />
      </div>

      {/* Import Modal */}
      {showImport && <ImportModal onClose={() => { setShowImport(false); fetchData(); }} />}
    </div>
  );
}

/* ── Course Card ─────────────────────────────────────────── */
function CourseCard({ seg, subscribed, onSubscribe, onUnsubscribe }: {
  seg: any; subscribed: boolean;
  onSubscribe: (id: number) => void; onUnsubscribe: (id: number) => void;
}) {
  const { user } = useAuth();
  const [isRestricted, setIsRestricted] = useState(seg.is_restricted === 1);
  const pct = seg.total_videos > 0 ? (seg.completed_videos / seg.total_videos * 100) : 0;
  const watchHrs = (seg.watch_seconds / 3600).toFixed(1);
  const desc = seg.description || `Access materials and track your progress in ${seg.name}.`;

  const handleRestrict = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const token = user?.token;
      if (!token) return;
      const res = await fetch(`/api/segments/${seg.id}/restrict`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIsRestricted(data.is_restricted);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="course-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <Link href={subscribed ? `/courses` : '#'} style={{ flex: 1, textDecoration: 'none', color: 'inherit', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div className="course-card-icon">{seg.icon}</div>
          {user?.username === 'vbsoni' && (
            <button 
              onClick={handleRestrict} 
              className={`btn btn-sm ${isRestricted ? 'btn-danger' : 'btn-secondary'}`}
              style={{ fontSize: 10, padding: '2px 6px', zIndex: 10 }}
            >
              {isRestricted ? 'Restricted' : 'Public'}
            </button>
          )}
        </div>
        <div className="course-card-name" title={seg.name}>{seg.name}</div>
        <div className="course-card-meta">
          {seg.total_videos} videos · {seg.completed_videos} completed<br />
          {watchHrs}h watched<br/>
          👥 {seg.enrolled_count || 0} enrolled
          {seg.uploaded_by_username && (
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--primary-light)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="online-dot" style={{ width: 6, height: 6, margin: 0, background: 'var(--primary-light)' }} />
              Shared by @{seg.uploaded_by_username}
            </div>
          )}
        </div>
        <div className="progress-outer" style={{ marginBottom: 8, marginTop: 'auto' }}>
          <div className="progress-inner" style={{ width: `${pct}%` }} />
        </div>
        <details style={{ fontSize: 13, color: 'var(--text-secondary)' }} onClick={e => e.preventDefault()}>
          <summary style={{ cursor: 'pointer', color: 'var(--primary-light)', fontWeight: 600, marginBottom: 4 }}>
            Description
          </summary>
          <p style={{ margin: '4px 0 0', lineHeight: 1.4, background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 6 }}>
            {desc}
          </p>
        </details>
      </Link>
      
      <div className="course-card-buttons" style={{ marginTop: 12 }}>
        {subscribed ? (
          <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => onUnsubscribe(seg.id)}>
            Unsubscribe
          </button>
        ) : (
          <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => onSubscribe(seg.id)}>
            Subscribe
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Leaderboard Card ────────────────────────────────────── */
function LeaderboardCard({ title, data }: { title: string; data: any[] }) {
  const medals = ['🥇', '🥈', '🥉'];
  const rankClass = ['gold', 'silver', 'bronze'];

  return (
    <div className="glass-card-static">
      <h5 style={{ marginTop: 0, color: 'var(--text-primary)', marginBottom: 12 }}>{title}</h5>
      {data.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No activity yet.</p>
      ) : (
        data.map((row, i) => (
          <div key={i} className="leaderboard-row">
            <div className={`lb-rank ${i < 3 ? rankClass[i] : ''}`}>
              {i < 3 ? medals[i] : `#${i + 1}`}
            </div>
            <div className="lb-name">{row.display_name}</div>
            <div className="lb-score">{(row.total_watch_sec / 3600).toFixed(1)}h</div>
          </div>
        ))
      )}
    </div>
  );
}

/* ── Import Modal ────────────────────────────────────────── */
function ImportModal({ onClose }: { onClose: () => void }) {
  const { token } = useAuth();
  const [url, setUrl] = useState('');
  const [icon, setIcon] = useState('▶️');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleImport = async () => {
    if (!url || !token) return;
    setLoading(true);
    setError('');
    try {
      await importApi.youtube(token, url, icon, desc);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">Upload a Course</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20 }}>
          Import a course using a YouTube Playlist URL.
        </p>
        <div className="form-group">
          <label className="label">YouTube Playlist URL</label>
          <input className="input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://youtube.com/playlist?..." />
        </div>
        <div className="form-group">
          <label className="label">Segment Icon (emoji)</label>
          <input className="input" value={icon} onChange={(e) => setIcon(e.target.value)} />
        </div>
        <div className="form-group">
          <label className="label">Description</label>
          <textarea className="input textarea" value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Optional description" />
        </div>
        {error && <div className="form-error">{error}</div>}
        <div className="flex-row mt-4" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleImport} disabled={loading}>
            {loading ? 'Importing...' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}
