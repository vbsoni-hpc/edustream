'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { friendsApi, usersApi, gamificationApi } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import Link from 'next/link';

export default function FriendsPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <FriendsContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function FriendsContent() {
  const { user, token } = useAuth();
  const [friends, setFriends] = useState<any[]>([]);
  const [incoming, setIncoming] = useState<any[]>([]);
  const [sent, setSent] = useState<any[]>([]);
  const [allUsers, setAllUsers] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'friends' | 'requests' | 'find'>('friends');

  const fetchData = async () => {
    if (!token) return;
    try {
      const [friendsRes, requestsRes, usersRes, lbRes] = await Promise.all([
        friendsApi.list(token),
        friendsApi.getRequests(token),
        usersApi.getAll(token),
        gamificationApi.getFriendLeaderboard(token),
      ]);
      setFriends(friendsRes.friends);
      setIncoming(requestsRes.incoming);
      setSent(requestsRes.sent);
      setAllUsers(usersRes.users);
      setLeaderboard(lbRes.leaderboard);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

  const handleAddFriend = async (friendId: number) => {
    if (!token) return;
    try {
      await friendsApi.add(token, friendId);
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to send request');
    }
  };

  const handleAccept = async (requestId: number) => {
    if (!token) return;
    await friendsApi.accept(token, requestId);
    fetchData();
  };

  const handleReject = async (requestId: number) => {
    if (!token) return;
    await friendsApi.reject(token, requestId);
    fetchData();
  };

  const handleRemove = async (friendId: number) => {
    if (!token) return;
    await friendsApi.remove(token, friendId);
    fetchData();
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading friends...</span></div>;
  }

  const friendIds = new Set(friends.map(f => f.id));
  const sentIds = new Set(sent.map(s => s.id));
  const incomingIds = new Set(incoming.map(i => i.id));

  const filteredUsers = allUsers.filter(u =>
    u.id !== user?.id &&
    !friendIds.has(u.id) &&
    (u.display_name?.toLowerCase().includes(search.toLowerCase()) ||
     u.username?.toLowerCase().includes(search.toLowerCase()))
  );

  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div className="animate-fade-in">
      <h1 className="hero-title">👥 Friends</h1>
      <p className="hero-subtitle" style={{ marginBottom: 24 }}>Study with your friends. See their progress. Finish together.</p>

      {/* Tabs */}
      <div className="tab-bar" style={{ marginBottom: 24 }}>
        <button className={`tab-btn ${tab === 'friends' ? 'active' : ''}`} onClick={() => setTab('friends')}>
          Friends ({friends.length})
        </button>
        <button className={`tab-btn ${tab === 'requests' ? 'active' : ''}`} onClick={() => setTab('requests')}>
          Requests {incoming.length > 0 && <span className="tab-badge">{incoming.length}</span>}
        </button>
        <button className={`tab-btn ${tab === 'find' ? 'active' : ''}`} onClick={() => setTab('find')}>
          Find People
        </button>
      </div>

      <div className="grid-2">
        {/* Left column: Content */}
        <div className="glass-card-static" style={{ padding: 0, overflow: 'hidden' }}>
          {tab === 'friends' && (
            <>
              {friends.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 32 }}>
                  <div style={{ fontSize: 40, marginBottom: 12 }}>👥</div>
                  <p style={{ color: 'var(--text-secondary)' }}>No friends yet. Find people to study with!</p>
                  <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => setTab('find')}>
                    Find People
                  </button>
                </div>
              ) : (
                <div>
                  <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-card)', fontWeight: 600, background: 'var(--bg-input)' }}>All Friends ({friends.length})</div>
                  {friends.map(f => (
                    <div key={f.id} className="fb-activity-item" style={{ padding: '16px 20px', alignItems: 'center' }}>
                      <Link href={`/profile/${f.username}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        <div className="fb-activity-icon" style={{ background: 'var(--primary)', color: 'white' }}>
                          {(f.display_name || '?')[0].toUpperCase()}
                        </div>
                      </Link>
                      <div className="fb-activity-content">
                        <Link href={`/profile/${f.username}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                          <div className="fb-activity-title">{f.display_name}</div>
                          <div className="fb-activity-meta">
                            {f.is_studying ? `Studying ${f.segment_name}` : f.is_online ? 'Online' : 'Offline'}
                          </div>
                        </Link>
                      </div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleRemove(f.id)}>
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {tab === 'requests' && (
            <>
              {incoming.length > 0 && (
                <div>
                  <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-card)', fontWeight: 600, background: 'var(--bg-input)' }}>Respond to Friend Requests</div>
                  {incoming.map(req => (
                    <div key={req.request_id} className="fb-activity-item" style={{ padding: '16px 20px', alignItems: 'center' }}>
                      <div className="fb-activity-icon">{(req.display_name || '?')[0].toUpperCase()}</div>
                      <div className="fb-activity-content">
                        <div className="fb-activity-title">{req.display_name}</div>
                        <div className="fb-activity-meta">@{req.username}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-primary btn-sm" onClick={() => handleAccept(req.request_id)}>Confirm</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleReject(req.request_id)}>Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {sent.length > 0 && (
                <div>
                  <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-card)', fontWeight: 600, background: 'var(--bg-input)' }}>Sent Requests</div>
                  {sent.map(req => (
                    <div key={req.request_id} className="fb-activity-item" style={{ padding: '16px 20px', alignItems: 'center' }}>
                      <div className="fb-activity-icon">{(req.display_name || '?')[0].toUpperCase()}</div>
                      <div className="fb-activity-content">
                        <div className="fb-activity-title">{req.display_name}</div>
                        <div className="fb-activity-meta">@{req.username} · Pending</div>
                      </div>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleReject(req.request_id)}>Cancel Request</button>
                    </div>
                  ))}
                </div>
              )}
              {incoming.length === 0 && sent.length === 0 && (
                <div style={{ textAlign: 'center', padding: 32 }}>
                  <p style={{ color: 'var(--text-secondary)' }}>No pending requests.</p>
                </div>
              )}
            </>
          )}

          {tab === 'find' && (
            <>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-card)', background: 'var(--bg-input)' }}>
                <input
                  className="input"
                  placeholder="Search for people..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{ background: 'var(--bg-card)' }}
                />
              </div>
              <div>
                {filteredUsers.slice(0, 20).map(u => (
                  <div key={u.id} className="fb-activity-item" style={{ padding: '16px 20px', alignItems: 'center' }}>
                    <Link href={`/profile/${u.username}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      <div className="fb-activity-icon">
                        {(u.display_name || '?')[0].toUpperCase()}
                      </div>
                    </Link>
                    <div className="fb-activity-content">
                      <div className="fb-activity-title">{u.display_name}</div>
                      <div className="fb-activity-meta">@{u.username}</div>
                    </div>
                    {sentIds.has(u.id) ? (
                      <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500 }}>Request Sent</span>
                    ) : incomingIds.has(u.id) ? (
                      <span style={{ fontSize: 13, color: 'var(--success)', fontWeight: 500 }}>Respond to Request</span>
                    ) : (
                      <button className="btn btn-secondary btn-sm" onClick={() => handleAddFriend(u.id)}>
                        <span style={{ marginRight: 4 }}>+</span> Add Friend
                      </button>
                    )}
                  </div>
                ))}
                {filteredUsers.length === 0 && search && (
                  <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 16 }}>No users found.</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* Right column: Friend Leaderboard */}
        <div>
          <div className="glass-card-static">
            <h4 className="section-title" style={{ margin: '0 0 16px' }}>🏆 Friend Leaderboard</h4>
            {leaderboard.length <= 1 ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Add friends to see your leaderboard!</p>
            ) : (
              leaderboard.map((entry, i) => (
                <div key={entry.id} className="leaderboard-row">
                  <div className={`lb-rank ${i < 3 ? ['gold', 'silver', 'bronze'][i] : ''}`}>
                    {i < 3 ? medals[i] : `#${i + 1}`}
                  </div>
                  <Link href={`/profile/${entry.username}`} className="lb-name" style={{ textDecoration: 'none', color: 'inherit' }}>
                    {entry.display_name}
                    {entry.id === user?.id && <span style={{ color: 'var(--primary-light)', marginLeft: 4 }}>(you)</span>}
                  </Link>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    {entry.current_streak > 0 && <span style={{ fontSize: 12 }}>🔥{entry.current_streak}</span>}
                    <div className="lb-score">⚡{entry.total_xp}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
