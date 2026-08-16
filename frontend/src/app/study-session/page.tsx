'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { sessionsApi, dashboardApi } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

export default function StudySessionPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <StudySessionContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function StudySessionContent() {
  const { user, token } = useAuth();
  const searchParams = useSearchParams();
  const sessionId = searchParams?.get('id');
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [segments, setSegments] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    if (!token) return;
    try {
      const [sessRes, segRes] = await Promise.all([
        sessionsApi.list(),
        dashboardApi.getSegmentStats(token),
      ]);
      setSessions(sessRes.sessions);
      setSegments(segRes.segments.filter((s: any) => s.name !== 'General' && s.name !== 'Uncategorized'));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

  // If ?id= is present, load that session
  useEffect(() => {
    if (sessionId && token) {
      sessionsApi.get(Number(sessionId)).then(data => setActiveSession(data)).catch(() => {});
    }
  }, [sessionId, token]);

  const handleJoin = async (id: number) => {
    if (!token) return;
    await sessionsApi.join(token, id);
    const data = await sessionsApi.get(id);
    setActiveSession(data);
    fetchData();
  };

  const handleLeave = async (id: number) => {
    if (!token) return;
    await sessionsApi.leave(token, id);
    setActiveSession(null);
    fetchData();
  };

  const handleEnd = async (id: number) => {
    if (!token) return;
    await sessionsApi.end(token, id);
    setActiveSession(null);
    fetchData();
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading sessions...</span></div>;
  }

  // Active session view
  if (activeSession) {
    const isCreator = activeSession.created_by === user?.id;
    return (
      <div className="animate-fade-in">
        <div className="flex-between" style={{ marginBottom: 24 }}>
          <button className="btn btn-ghost" onClick={() => setActiveSession(null)}>← Back to Sessions</button>
        </div>

        <div className="session-hero">
          <div className="session-hero-icon">{activeSession.segment_icon || '📚'}</div>
          <div>
            <h2 className="session-hero-title">{activeSession.title || activeSession.segment_name}</h2>
            <p className="session-hero-meta">
              {activeSession.video_title && `📹 ${activeSession.video_title} · `}
              Created by {activeSession.creator_name}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {isCreator ? (
              <button className="btn btn-danger" onClick={() => handleEnd(activeSession.id)}>End Session</button>
            ) : (
              <button className="btn btn-ghost" onClick={() => handleLeave(activeSession.id)}>Leave</button>
            )}
          </div>
        </div>

        {/* Members */}
        <div className="glass-card-static" style={{ marginTop: 24 }}>
          <h4 className="section-title" style={{ margin: '0 0 16px' }}>
            👥 Studying Together ({activeSession.members?.length || 0})
          </h4>
          <div className="presence-list">
            {activeSession.members?.map((member: any) => (
              <Link key={member.id} href={`/profile/${member.username}`} className="presence-item" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="presence-avatar">
                  <span className="online-dot-pulse" />
                  {(member.display_name || '?')[0].toUpperCase()}
                </div>
                <div className="presence-info">
                  <div className="presence-name">{member.display_name}</div>
                  <div className="presence-course">@{member.username}</div>
                </div>
                {member.id === activeSession.created_by && (
                  <span className="presence-badge" style={{ background: 'var(--primary)' }}>Host</span>
                )}
              </Link>
            ))}
          </div>
        </div>

        {/* Study area with course link */}
        <div className="glass-card-static" style={{ marginTop: 24, textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📚</div>
          <h3>Study Area</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
            Open the course player to study along with your session members.
          </p>
          <Link href="/player" className="btn btn-primary">
            Open Player →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="hero-title">📡 Study Sessions</h1>
          <p className="hero-subtitle">Join a session to study together in real-time.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + New Session
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="glass-card-static" style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📡</div>
          <h3>No active study sessions</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
            Start a session and invite your friends to study together!
          </p>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            Create Study Session
          </button>
        </div>
      ) : (
        <div className="session-grid">
          {sessions.map(session => (
            <div key={session.id} className="session-card">
              <div className="session-card-header">
                <span className="session-card-icon">{session.segment_icon || '📚'}</span>
                <div>
                  <div className="session-card-title">{session.title || session.segment_name}</div>
                  <div className="session-card-meta">
                    by {session.creator_name}
                    {session.video_title && ` · ${session.video_title}`}
                  </div>
                </div>
              </div>
              <div className="session-card-members">
                <span className="session-member-count">
                  👥 {session.member_count} studying
                </span>
                <span className="session-live-badge">
                  <span className="online-dot-pulse" style={{ position: 'relative', display: 'inline-block', width: 6, height: 6 }} />
                  Live
                </span>
              </div>
              <button className="btn btn-primary btn-sm" style={{ width: '100%', marginTop: 12 }} onClick={() => handleJoin(session.id)}>
                Join Session
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && <CreateSessionModal segments={segments} onClose={() => { setShowCreate(false); fetchData(); }} />}
    </div>
  );
}

function CreateSessionModal({ segments, onClose }: { segments: any[]; onClose: () => void }) {
  const { token } = useAuth();
  const [segmentId, setSegmentId] = useState<number>(0);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!token || !segmentId) return;
    setLoading(true);
    try {
      await sessionsApi.create(token, { segment_id: segmentId, title: title || undefined });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3 className="modal-title">Create Study Session</h3>
        <div className="form-group">
          <label className="label">Course</label>
          <select className="input" value={segmentId} onChange={e => setSegmentId(Number(e.target.value))}>
            <option value={0}>Select a course...</option>
            {segments.map(s => (
              <option key={s.id} value={s.id}>{s.icon} {s.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="label">Session Title (Optional)</label>
          <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Chapter 5 Review" />
        </div>
        <div className="flex-row mt-4" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleCreate} disabled={loading || !segmentId}>
            {loading ? 'Creating...' : 'Create Session'}
          </button>
        </div>
      </div>
    </div>
  );
}
