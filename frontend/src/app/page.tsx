'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { dashboardApi, subscriptionsApi, importApi, presenceApi, trendingApi, gamificationApi, sessionsApi } from '@/lib/api';
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
  // New social state
  const [activeLearners, setActiveLearners] = useState<any[]>([]);
  const [trendingCourses, setTrendingCourses] = useState<any[]>([]);
  const [xpData, setXpData] = useState<any>(null);
  const [streakData, setStreakData] = useState<any>(null);
  const [sessions, setSessions] = useState<any[]>([]);

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

      // Fetch social data (non-blocking)
      Promise.all([
        presenceApi.getActive().then(r => setActiveLearners(r.learners)),
        trendingApi.getCourses().then(r => setTrendingCourses(r.courses)),
        gamificationApi.getXP(token).then(r => setXpData(r)),
        gamificationApi.getStreak(token).then(r => setStreakData(r)),
        sessionsApi.list().then(r => setSessions(r.sessions)),
      ]).catch(() => {});
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

  // Refresh presence every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      presenceApi.getActive().then(r => setActiveLearners(r.learners)).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

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
    <div className="animate-fade-in learning-feed">
      {/* Notices */}
      {notices.length > 0 && (
        <div className="mb-4">
          {notices.map((n: any) => (
            <div key={n.id} className="notice-banner">{n.content}</div>
          ))}
        </div>
      )}

      {/* Stats Bar — XP, Streak, Level */}
      <div className="stats-bar">
        <div className="stat-pill">
          <span className="stat-pill-icon">⚡</span>
          <div>
            <div className="stat-pill-value">{xpData?.total_xp || 0} XP</div>
            <div className="stat-pill-label">Level {xpData?.level || 1}</div>
          </div>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-icon">🔥</span>
          <div>
            <div className="stat-pill-value">{streakData?.current_streak || 0} day{(streakData?.current_streak || 0) !== 1 ? 's' : ''}</div>
            <div className="stat-pill-label">Streak</div>
          </div>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-icon">✅</span>
          <div>
            <div className="stat-pill-value">{stats?.completed_videos || 0}</div>
            <div className="stat-pill-label">Lectures Done</div>
          </div>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-icon">⏱️</span>
          <div>
            <div className="stat-pill-value">{formatHours(stats?.total_watch_seconds || 0)}</div>
            <div className="stat-pill-label">Watch Time</div>
          </div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <button className="btn btn-secondary upload-course-btn" onClick={() => setShowImport(true)}>
            ➕ <span className="btn-text">Upload Course</span>
          </button>
        </div>
      </div>

      {/* Continue Learning Hero */}
      {lastSeg && (
        <Link href="/player" style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
          <div className="continue-card">
            <div className="continue-card-glow" />
            <div className="continue-card-content">
              <div className="continue-card-label">Continue Learning</div>
              <div className="continue-card-title">{lastSeg.icon} {lastSeg.name}</div>
              <div className="continue-card-meta">
                {lastSeg.completed_videos}/{lastSeg.total_videos} lectures · {formatHours(lastSeg.watch_seconds)} watched
              </div>
              <div className="progress-outer" style={{ marginTop: 12, height: 8 }}>
                <div
                  className="progress-inner"
                  style={{ width: `${lastSeg.total_videos > 0 ? (lastSeg.completed_videos / lastSeg.total_videos * 100) : 0}%` }}
                />
              </div>
            </div>
            <div className="continue-card-action">Continue →</div>
          </div>
        </Link>
      )}

      {/* Two-column: People Studying Now + Active Study Sessions */}
      <div className="grid-2" style={{ marginTop: 24 }}>
        {/* 🟢 People Studying Now */}
        <div className="glass-card-static presence-card">
          <div className="flex-between" style={{ marginBottom: 12 }}>
            <h4 className="section-title" style={{ margin: 0 }}>🟢 People Studying Now</h4>
            <span className="presence-count">{activeLearners.length} online</span>
          </div>
          {activeLearners.length === 0 ? (
            <p className="empty-state-text" style={{ fontSize: 13 }}>No one is studying right now. Be the first! 🚀</p>
          ) : (
            <div className="presence-list">
              {activeLearners.slice(0, 8).map((learner: any) => (
                <Link key={learner.id} href={`/profile/${learner.username}`} className="presence-item">
                  <div className="presence-avatar">
                    <span className="online-dot-pulse" />
                    {(learner.display_name || learner.username || '?')[0].toUpperCase()}
                  </div>
                  <div className="presence-info">
                    <div className="presence-name">{learner.display_name}</div>
                    <div className="presence-course">
                      {learner.segment_icon} {learner.segment_name || 'Browsing'}
                    </div>
                  </div>
                  {learner.current_video_id && (
                    <div className="presence-badge">Studying</div>
                  )}
                </Link>
              ))}
              {activeLearners.length > 8 && (
                <div className="presence-more">+{activeLearners.length - 8} more</div>
              )}
            </div>
          )}
        </div>

        {/* 📡 Active Study Sessions */}
        <div className="glass-card-static">
          <div className="flex-between" style={{ marginBottom: 12 }}>
            <h4 className="section-title" style={{ margin: 0 }}>📡 Study Sessions</h4>
            <Link href="/study-session" className="btn btn-ghost btn-sm">View All</Link>
          </div>
          {sessions.length === 0 ? (
            <p className="empty-state-text" style={{ fontSize: 13 }}>No active study sessions. Start one from a course page!</p>
          ) : (
            <div className="presence-list">
              {sessions.slice(0, 5).map((session: any) => (
                <Link key={session.id} href={`/study-session?id=${session.id}`} className="presence-item">
                  <div className="presence-avatar session-avatar">
                    {session.segment_icon || '📚'}
                  </div>
                  <div className="presence-info">
                    <div className="presence-name">{session.title || session.segment_name}</div>
                    <div className="presence-course">
                      {session.member_count} studying · by {session.creator_name}
                    </div>
                  </div>
                  <div className="presence-badge session-badge">Join</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 🔥 Trending Courses */}
      {trendingCourses.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h4 className="section-title">🔥 Trending Courses</h4>
          <div className="carousel mb-6">
            {trendingCourses.map((course: any) => (
              <div key={course.id} className="trending-card">
                <div className="trending-card-icon">{course.icon}</div>
                <div className="trending-card-name">{course.name}</div>
                <div className="trending-card-stats">
                  <span>👥 {course.enrolled_count} learners</span>
                  {course.studying_now > 0 && (
                    <span className="trending-live">
                      <span className="online-dot-pulse" style={{ position: 'relative', display: 'inline-block', width: 6, height: 6, marginRight: 4 }} />
                      {course.studying_now} now
                    </span>
                  )}
                </div>
                <div className="trending-card-activity">
                  {course.active_24h > 0 && <span>{course.active_24h} active today</span>}
                  {course.completions_7d > 0 && <span>{course.completions_7d} completions this week</span>}
                </div>
                {!subscribedIds.has(course.id) ? (
                  <button className="btn btn-secondary btn-sm" style={{ marginTop: 8, width: '100%' }} onClick={() => handleSubscribe(course.id)}>
                    Subscribe
                  </button>
                ) : (
                  <Link href="/courses" className="btn btn-ghost btn-sm" style={{ marginTop: 8, width: '100%', display: 'block', textAlign: 'center' }}>
                    Continue →
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 📚 My Courses */}
      <h4 className="section-title" style={{ marginTop: 32 }}>📚 My Courses</h4>
      {myCourses.length === 0 ? (
        <div className="empty-state" style={{ padding: '24px' }}>
          <p className="empty-state-text">No courses subscribed yet. Browse Trending or All Courses below and subscribe!</p>
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

      {/* 🌐 All Courses */}
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

      {/* 🏆 Leaderboards */}
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
      </Link>
      <details style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
        <summary style={{ cursor: 'pointer', color: 'var(--primary-light)', fontWeight: 600, marginBottom: 4 }}>
          Description
        </summary>
        <p style={{ margin: '4px 0 0', lineHeight: 1.4, background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 6 }}>
          {desc}
        </p>
      </details>
      
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
  const [source, setSource] = useState<'youtube' | 'telegram'>('youtube');
  const [url, setUrl] = useState('');
  const [channel, setChannel] = useState('');
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('▶️');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleImport = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      if (source === 'youtube') {
        if (!url) throw new Error('URL is required');
        await importApi.youtube(token, url, icon, desc);
      } else {
        if (!channel) throw new Error('Channel username is required');
        await importApi.telegram(token, channel, name, icon, desc);
      }
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
        
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <button 
            className={`btn btn-sm ${source === 'youtube' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => { setSource('youtube'); setIcon('▶️'); }}
          >
            YouTube Playlist
          </button>
          <button 
            className={`btn btn-sm ${source === 'telegram' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => { setSource('telegram'); setIcon('📱'); }}
          >
            Telegram Channel
          </button>
        </div>

        {source === 'youtube' ? (
          <div className="form-group">
            <label className="label">YouTube Playlist URL</label>
            <input className="input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://youtube.com/playlist?..." />
          </div>
        ) : (
          <>
            <div className="form-group">
              <label className="label">Telegram Channel Username</label>
              <input className="input" value={channel} onChange={(e) => setChannel(e.target.value)} placeholder="@course_channel" />
            </div>
            <div className="form-group">
              <label className="label">Course Name (Optional)</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Advanced Mathematics" />
            </div>
          </>
        )}

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
