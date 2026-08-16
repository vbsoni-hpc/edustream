'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { adminApi, coursesApi, importApi, analyticsApi } from '@/lib/api';
import { formatDate, timeAgo } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';

export default function AdminPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <AdminContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function AdminContent() {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState('sync');

  if (!user?.is_admin) {
    return (
      <div className="empty-state" style={{ marginTop: 60 }}>
        <div className="empty-state-icon">🔒</div>
        <p className="empty-state-text">Admin access required.</p>
      </div>
    );
  }

  const tabs = [
    { key: 'sync', label: '🔄 Sync' },
    { key: 'segments', label: '📁 Segments' },
    { key: 'modules', label: '📂 Modules' },
    { key: 'videos', label: '▶️ Videos' },
    { key: 'notices', label: '📢 Notices' },
    { key: 'users', label: '👥 Users' },
    { key: 'tools', label: '🔧 Tools' },
  ];

  return (
    <div className="animate-fade-in">
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 24 }}>⚙️ Admin Panel</h1>

      <div className="tabs" style={{ flexWrap: 'wrap' }}>
        {tabs.map(t => (
          <button key={t.key} className={`tab ${activeTab === t.key ? 'active' : ''}`} onClick={() => setActiveTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'sync' && <SyncSection />}
      {activeTab === 'segments' && <SegmentsSection />}
      {activeTab === 'modules' && <ModulesSection />}
      {activeTab === 'videos' && <VideosSection />}
      {activeTab === 'notices' && <NoticesSection />}
      {activeTab === 'users' && <UsersSection />}
      {activeTab === 'tools' && <ToolsSection />}
    </div>
  );
}

/* ── Sync Section ────────────────────────────────────────── */
function SyncSection() {
  const { token } = useAuth();
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState('');

  const handleSync = async () => {
    if (!token) return;
    setSyncing(true);
    setResult('');
    try {
      const res = await adminApi.sync(token);
      setResult(`✅ Synced ${res.synced} videos from Telegram channel.`);
    } catch (err: any) {
      setResult(`❌ Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="glass-card-static">
      <h3 style={{ marginBottom: 12 }}>Telegram Channel Sync</h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 16 }}>
        Sync your Telegram channel to import new videos.
      </p>
      <button className="btn btn-primary" onClick={handleSync} disabled={syncing}>
        {syncing ? '⏳ Syncing...' : '🔄 Sync Now'}
      </button>
      {result && <div className="notice-banner mt-4">{result}</div>}
    </div>
  );
}

/* ── Segments Section ────────────────────────────────────── */
function SegmentsSection() {
  const { token } = useAuth();
  const [segments, setSegments] = useState<any[]>([]);
  const [newName, setNewName] = useState('');
  const [newIcon, setNewIcon] = useState('📁');
  const [newDesc, setNewDesc] = useState('');

  const load = async () => {
    if (!token) return;
    const res = await coursesApi.getSegments(token);
    setSegments(res.segments);
  };

  useEffect(() => { load(); }, [token]);

  const handleCreate = async () => {
    if (!token || !newName) return;
    await adminApi.createSegment(token, { name: newName, icon: newIcon, description: newDesc });
    setNewName(''); setNewIcon('📁'); setNewDesc('');
    load();
  };

  const handleToggleRestrict = async (id: number, current: boolean) => {
    if (!token) return;
    try {
      await adminApi.updateSegment(token, id, { is_restricted: !current });
      load();
    } catch (e) {
      console.error(e);
    }
  };


  const handleEdit = async (segment: any) => {
    const newName = window.prompt("Enter new segment name:", segment.name);
    if (!newName) return;
    try {
      await adminApi.updateSegment(token!, segment.id, { name: newName });
      load();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (segmentId: number) => {
    if (!window.confirm("Are you sure? This will delete all modules and videos in this segment!")) return;
    try {
      await adminApi.deleteSegment(token!, segmentId);
      load();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="glass-card-static mb-6">
        <h4 style={{ marginBottom: 12 }}>Create Segment</h4>
        <div className="flex-row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <input className="input" style={{ maxWidth: 200 }} placeholder="Name" value={newName} onChange={e => setNewName(e.target.value)} />
          <input className="input" style={{ maxWidth: 60 }} placeholder="Icon" value={newIcon} onChange={e => setNewIcon(e.target.value)} />
          <input className="input" style={{ flex: 1 }} placeholder="Description" value={newDesc} onChange={e => setNewDesc(e.target.value)} />
          <button className="btn btn-primary" onClick={handleCreate}>Create</button>
        </div>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th><th>Icon</th><th>Name</th><th>Description</th><th>Restricted</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {segments.map(s => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>{s.icon}</td>
              <td>{s.name}</td>
              <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{s.description || '—'}</td>
              <td>
                <button 
                  className={`btn btn-sm ${s.is_restricted ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ fontSize: 11, padding: '4px 8px' }}
                  onClick={() => handleToggleRestrict(s.id, s.is_restricted)}
                >
                  {s.is_restricted ? 'Yes (Restricted)' : 'No (Public)'}

                </button>
              </td>
              <td>
                <button className="btn btn-sm btn-secondary" style={{ marginRight: 4 }} onClick={() => handleEdit(s)}>✏️</button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.id)}>🗑️</button>
              </td>
            </tr>

          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Modules Section ─────────────────────────────────────── */
function ModulesSection() {
  const { token } = useAuth();
  const [segments, setSegments] = useState<any[]>([]);
  const [modules, setModules] = useState<any[]>([]);
  const [newName, setNewName] = useState('');
  const [newIcon, setNewIcon] = useState('📂');
  const [newSegId, setNewSegId] = useState('');

  const load = async () => {
    if (!token) return;
    const resSegs = await coursesApi.getSegments(token);
    setSegments(resSegs.segments);
    
    // Fetch all modules (using analytics endpoint which returns all)
    const resMods = await analyticsApi.getModules(token);
    setModules(resMods.modules || []);
  };

  useEffect(() => { load(); }, [token]);

  const handleCreate = async () => {
    if (!token || !newName || !newSegId) return;
    await adminApi.createModule(token, { name: newName, segment_id: parseInt(newSegId), icon: newIcon });
    setNewName(''); setNewIcon('📂');
    load();
  };

  const handleToggleRestrict = async (id: number, current: boolean) => {
    if (!token) return;
    try {
      await adminApi.updateModule(token, id, { is_restricted: !current });
      load();
    } catch (e) {
      console.error(e);
    }
  };


  const handleEdit = async (module: any) => {
    const newName = window.prompt("Enter new module name:", module.name);
    if (!newName) return;
    try {
      await adminApi.updateModule(token!, module.id, { name: newName });
      load();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (moduleId: number) => {
    if (!window.confirm("Are you sure? This will unassign all videos in this module!")) return;
    try {
      await adminApi.deleteModule(token!, moduleId);
      load();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="glass-card-static mb-6">
        <h4 style={{ marginBottom: 12 }}>Create Module</h4>
        <div className="flex-row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <select className="select" style={{ maxWidth: 200 }} value={newSegId} onChange={e => setNewSegId(e.target.value)}>
            <option value="">Select Segment</option>
            {segments.map(s => <option key={s.id} value={s.id}>{s.icon} {s.name}</option>)}
          </select>
          <input className="input" style={{ maxWidth: 200 }} placeholder="Module Name" value={newName} onChange={e => setNewName(e.target.value)} />
          <input className="input" style={{ maxWidth: 60 }} placeholder="Icon" value={newIcon} onChange={e => setNewIcon(e.target.value)} />
          <button className="btn btn-primary" onClick={handleCreate}>Create</button>
        </div>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th><th>Icon</th><th>Name</th><th>Segment</th><th>Restricted</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {modules.map(m => (
            <tr key={m.id}>
              <td>{m.id}</td>
              <td>{m.icon}</td>
              <td>{m.name}</td>
              <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{m.segment_name || '—'}</td>
              <td>
                <button 
                  className={`btn btn-sm ${m.is_restricted ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ fontSize: 11, padding: '4px 8px' }}
                  onClick={() => handleToggleRestrict(m.id, m.is_restricted)}
                >
                  {m.is_restricted ? 'Yes (Restricted)' : 'No (Public)'}

                </button>
              </td>
              <td>
                <button className="btn btn-sm btn-secondary" style={{ marginRight: 4 }} onClick={() => handleEdit(m)}>✏️</button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(m.id)}>🗑️</button>
              </td>
            </tr>

          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Videos Section ──────────────────────────────────────── */
function VideosSection() {
  const { token } = useAuth();
  const [videos, setVideos] = useState<any[]>([]);

  const load = async () => {
    if (!token) return;
    try {
      const res = await coursesApi.getVideos(token);
      setVideos(res.videos || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { load(); }, [token]);

  const handleToggleRestrict = async (id: number, current: boolean) => {
    if (!token) return;
    try {
      await adminApi.setVideoRestricted(token, id, !current);
      load();
    } catch (e) {
      console.error(e);
    }
  };


  const handleEdit = async (video: any) => {
    const newTitle = window.prompt("Enter new video title:", video.title);
    if (!newTitle) return;
    try {
      await adminApi.updateVideo(token!, video.id, { title: newTitle });
      load();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (videoId: number) => {
    if (!window.confirm("Are you sure you want to delete this video?")) return;
    try {
      await adminApi.deleteVideo(token!, videoId);
      load();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="glass-card-static mb-6">
        <h4 style={{ marginBottom: 4 }}>All Videos</h4>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Manage video restrictions.</p>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th><th>Title</th><th>Duration</th><th>Restricted</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {videos.map(v => (
            <tr key={v.id}>
              <td>{v.id}</td>
              <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.title}</td>
              <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{Math.floor(v.duration / 60)}:{(v.duration % 60).toString().padStart(2, '0')}</td>
              <td>
                <button 
                  className={`btn btn-sm ${v.is_restricted ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ fontSize: 11, padding: '4px 8px' }}
                  onClick={() => handleToggleRestrict(v.id, v.is_restricted)}
                >
                  {v.is_restricted ? 'Yes (Restricted)' : 'No (Public)'}

                </button>
              </td>
              <td>
                <button className="btn btn-sm btn-secondary" style={{ marginRight: 4 }} onClick={() => handleEdit(v)}>✏️</button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(v.id)}>🗑️</button>
              </td>
            </tr>

          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Notices Section ─────────────────────────────────────── */
function NoticesSection() {
  const { token } = useAuth();
  const [notices, setNotices] = useState<any[]>([]);
  const [newContent, setNewContent] = useState('');

  const load = async () => {
    if (!token) return;
    const res = await adminApi.getNotices(token);
    setNotices(res.notices);
  };

  useEffect(() => { load(); }, [token]);

  const handleCreate = async () => {
    if (!token || !newContent) return;
    await adminApi.createNotice(token, newContent);
    setNewContent('');
    load();
  };

  const handleDelete = async (id: number) => {
    if (!token) return;
    await adminApi.deleteNotice(token, id);
    load();
  };

  return (
    <div>
      <div className="glass-card-static mb-6">
        <h4 style={{ marginBottom: 12 }}>Post a Notice</h4>
        <textarea className="input textarea" value={newContent} onChange={e => setNewContent(e.target.value)} placeholder="Notice content (supports markdown)" />
        <button className="btn btn-primary mt-4" onClick={handleCreate}>Post Notice</button>
      </div>

      {notices.map(n => (
        <div key={n.id} className="notice-banner flex-between">
          <div>
            <div>{n.content}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{formatDate(n.created_at)}</div>
          </div>
          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(n.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

/* ── Users Section ───────────────────────────────────────── */
function UsersSection() {
  const { token } = useAuth();
  const [users, setUsers] = useState<any[]>([]);

  const load = async () => {
    if (!token) return;
    const res = await adminApi.getUsers(token);
    setUsers(res.users);
  };

  useEffect(() => { load(); }, [token]);

  const handleDelete = async (id: number) => {
    if (!token || !confirm('Delete this user?')) return;
    await adminApi.deleteUser(token, id);
    load();
  };

  const toggleAdmin = async (u: any) => {
    if (!token) return;
    await adminApi.updateUser(token, u.id, {
      username: u.username,
      display_name: u.display_name,
      is_admin: !u.is_admin,
    });
    load();
  };

  return (
    <table className="admin-table">
      <thead>
        <tr>
          <th>ID</th><th>Username</th><th>Display Name</th><th>Admin</th><th>Last Active</th><th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map(u => (
          <tr key={u.id}>
            <td>{u.id}</td>
            <td>{u.username}</td>
            <td>{u.display_name}</td>
            <td>
              <button className={`badge ${u.is_admin ? 'badge-success' : 'badge-primary'}`} onClick={() => toggleAdmin(u)} style={{ cursor: 'pointer' }}>
                {u.is_admin ? 'Admin' : 'User'}
              </button>
            </td>
            <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              {u.last_active > 0 ? timeAgo(u.last_active) : 'Never'}
            </td>
            <td>
              <button className="btn btn-danger btn-sm" onClick={() => handleDelete(u.id)}>Delete</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ── Tools Section ───────────────────────────────────────── */
function ToolsSection() {
  const { token } = useAuth();
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleBackup = async () => {
    if (!token) return;
    setLoading(true);
    try {
      await adminApi.backup(token);
      setResult('✅ Backup triggered successfully.');
    } catch (err: any) {
      setResult(`❌ ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFixYoutube = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await adminApi.fixYoutube(token);
      setResult(`✅ Recovered ${res.recovered} missing YouTube IDs.`);
    } catch (err: any) {
      setResult(`❌ ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearMessages = async () => {
    if (!token || !confirm('Delete ALL messages? This cannot be undone.')) return;
    try {
      await fetch('/api/messages', { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
      setResult('✅ All messages deleted.');
    } catch (err: any) {
      setResult(`❌ ${err.message}`);
    }
  };

  return (
    <div className="flex-col" style={{ gap: 16 }}>
      <div className="glass-card-static flex-between">
        <div>
          <h4>GitHub Backup</h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Force a database backup to GitHub.</p>
        </div>
        <button className="btn btn-secondary" onClick={handleBackup} disabled={loading}>💾 Backup Now</button>
      </div>

      <div className="glass-card-static flex-between">
        <div>
          <h4>Recover YouTube IDs</h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Attempt to repair missing YouTube video IDs.</p>
        </div>
        <button className="btn btn-secondary" onClick={handleFixYoutube} disabled={loading}>🔧 Fix YouTube</button>
      </div>

      <div className="glass-card-static flex-between">
        <div>
          <h4>Clear All Messages</h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Delete all group chat and DM messages.</p>
        </div>
        <button className="btn btn-danger" onClick={handleClearMessages}>🗑️ Clear Messages</button>
      </div>

      {result && <div className="notice-banner">{result}</div>}
    </div>
  );
}
