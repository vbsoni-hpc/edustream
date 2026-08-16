'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { profileApi, friendsApi, blogsApi } from '@/lib/api';
import AuthGuard from '@/components/AuthGuard';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function ProfilePage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <main className="main-content">
          <ProfileContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function ProfileContent() {
  const params = useParams();
  const username = params.username as string;
  const { user, token } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [friendship, setFriendship] = useState<any>(null);
  const [blogs, setBlogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    profileApi.get(username).then(p => {
      setProfile(p);
      if (token && p.id !== user?.id) {
        friendsApi.status(token, p.id).then(r => setFriendship(r.friendship)).catch(() => {});
      }
      blogsApi.getUserBlogs(token || '', username, 20, 0).then(r => setBlogs(r.blogs || [])).catch(() => {});
    }).catch(() => {
      setProfile(null);
    }).finally(() => setLoading(false));
  }, [username, token]);

  const handleAddFriend = async () => {
    if (!token || !profile) return;
    try {
      await friendsApi.add(token, profile.id);
      const r = await friendsApi.status(token, profile.id);
      setFriendship(r.friendship);
    } catch {}
  };

  const handleRemoveFriend = async () => {
    if (!token || !profile) return;
    await friendsApi.remove(token, profile.id);
    setFriendship(null);
  };

  const handleAcceptFriend = async () => {
    if (!token || !friendship) return;
    await friendsApi.accept(token, friendship.request_id);
    const r = await friendsApi.status(token, profile.id);
    setFriendship(r.friendship);
  };

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading profile...</span></div>;
  }

  if (!profile) {
    return (
      <div className="animate-fade-in" style={{ textAlign: 'center', padding: 48 }}>
        <h2>User not found</h2>
        <p style={{ color: 'var(--text-secondary)' }}>The user @{username} doesn&#39;t exist.</p>
        <Link href="/" className="btn btn-primary" style={{ marginTop: 16 }}>Go Home</Link>
      </div>
    );
  }

  const isOwnProfile = user?.username === profile.username;

  const statusText = profile.is_studying ? '🟢 Studying' :
                     profile.is_online ? '🟢 Online' : '⚫ Offline';

  const friendshipButton = () => {
    if (isOwnProfile) return null;
    if (!friendship) {
      return <button className="btn btn-primary" onClick={handleAddFriend}>Add Friend</button>;
    }
    if (friendship.status === 'accepted') {
      return <button className="btn btn-ghost" onClick={handleRemoveFriend}>Remove Friend</button>;
    }
    if (friendship.status === 'pending') {
      if (friendship.friend_id === user?.id) {
        return <button className="btn btn-primary" onClick={handleAcceptFriend}>Accept Request</button>;
      }
      return <button className="btn btn-ghost" disabled>Request Sent</button>;
    }
    return null;
  };

  return (
    <div className="fb-profile-container animate-fade-in">
      {isEditing && (
        <EditProfileModal 
          profile={profile} 
          token={token || ''} 
          onClose={() => setIsEditing(false)} 
          onSave={(p) => setProfile(p)} 
        />
      )}

      {/* Profile Cover & Header */}
      <div className="fb-profile-header">
        <div className="fb-cover-photo" style={{ backgroundImage: profile.cover_url ? `url(${profile.cover_url})` : undefined, backgroundSize: "cover", backgroundPosition: "center" }} />
        
        <div className="fb-profile-avatar-wrapper">
          <div className="fb-profile-avatar" style={{ backgroundImage: profile.avatar_url ? `url(${profile.avatar_url})` : undefined, backgroundSize: "cover", backgroundPosition: "center", color: profile.avatar_url ? 'transparent' : 'inherit' }}>
            {(profile.display_name || '?')[0].toUpperCase()}
          </div>
          {profile.is_studying && <span className="online-dot-pulse" style={{ position: 'absolute', bottom: 12, right: 12, width: 20, height: 20, border: '3px solid var(--bg-card)' }} />}
        </div>
        
        <div className="fb-profile-info">
          <h1 className="fb-profile-name">{profile.display_name}</h1>
          <p className="fb-profile-handle">
            @{profile.username} • {profile.level} Lvl 
            {profile.institute && <span> • 🏫 {profile.institute}</span>}
          </p>
        </div>
        
        <div className="fb-profile-actions">
          {isOwnProfile ? (
            <button className="btn btn-secondary" onClick={() => setIsEditing(true)}>Edit Profile</button>
          ) : (
            friendshipButton()
          )}
        </div>
      </div>

      <div className="fb-profile-body">
        {/* Left Column (Sidebar) */}
        <div className="fb-profile-sidebar">

          {/* Blogs Options */}
          {isOwnProfile && (
            <div className="glass-card-static" style={{ marginBottom: 16 }}>
              <h3 className="fb-card-title">Blogs</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <Link href="/blogs" className="shortcut-item" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 8, borderRadius: 8, color: 'var(--text-primary)', fontWeight: 500, textDecoration: 'none' }}>
                  <span style={{ fontSize: 20 }}>📰</span> All Blogs
                </Link>
                <Link href={`/blogs?user=${user?.username}`} className="shortcut-item" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 8, borderRadius: 8, color: 'var(--text-primary)', fontWeight: 500, textDecoration: 'none' }}>
                  <span style={{ fontSize: 20 }}>👤</span> My Blogs
                </Link>
                <Link href="/blogs/new" className="shortcut-item" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 8, borderRadius: 8, color: 'var(--text-primary)', fontWeight: 500, textDecoration: 'none' }}>
                  <span style={{ fontSize: 20 }}>✍️</span> Write a Post
                </Link>
              </div>
            </div>
          )}

          
          {/* About / Intro */}
          <div className="glass-card-static">
            <h3 className="fb-card-title">Intro</h3>

            {profile.bio && <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-primary)', textAlign: 'center' }}>{profile.bio}</div>}
            {profile.work && (
              <div className="fb-stat-row">
                <span className="fb-stat-icon">💼</span>
                <span>Works at <strong>{profile.work}</strong></span>
              </div>
            )}
            {profile.location && (
              <div className="fb-stat-row">
                <span className="fb-stat-icon">📍</span>
                <span>Lives in <strong>{profile.location}</strong></span>
              </div>
            )}

            <div className="fb-stat-row">
              <span className="fb-stat-icon">🎓</span>
              <span><strong>{profile.completed_courses}</strong> courses completed</span>
            </div>
            <div className="fb-stat-row">
              <span className="fb-stat-icon">✅</span>
              <span><strong>{profile.completed_lectures}</strong> lectures done</span>
            </div>
            <div className="fb-stat-row">
              <span className="fb-stat-icon">⏱️</span>
              <span><strong>{profile.total_watch_hours}</strong> hours watched</span>
            </div>
            <div className="fb-stat-row">
              <span className="fb-stat-icon">🔥</span>
              <span><strong>{profile.current_streak}</strong> day streak (Best: {profile.longest_streak})</span>
            </div>
            
            <div style={{ marginTop: 16 }}>
              <div className="flex-between" style={{ marginBottom: 4, fontSize: 13, color: 'var(--text-secondary)' }}>
                <span>XP Progress</span>
                <span>{profile.total_xp % 500}/500 XP</span>
              </div>
              <div className="progress-outer" style={{ height: 6 }}>
                <div className="progress-inner" style={{ width: `${(profile.total_xp % 500) / 5}%`, background: 'var(--primary)' }} />
              </div>
            </div>
          </div>

          {/* Friends Preview (Mock for now, could load real friends later) */}
          <div className="glass-card-static">
            <div className="flex-between" style={{ borderBottom: '1px solid var(--border-card)', paddingBottom: 12, marginBottom: 12 }}>
              <h3 style={{ fontSize: 18, fontWeight: 600 }}>Friends</h3>
              <span style={{ color: 'var(--primary)', fontSize: 14, cursor: 'pointer' }}>See All</span>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 14, textAlign: 'center', padding: '16px 0' }}>
              Friends list is private
            </div>
          </div>
          
        </div>

        {/* Right Column (Wall / Activity) */}
        <div className="fb-profile-main">
          {/* Blogs / Wall */}
          {blogs.length > 0 && (
            <div className="glass-card-static" style={{ marginBottom: 24 }}>
              <h3 className="fb-card-title">📝 Posts</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {blogs.map(blog => (
                  <div key={blog.id} className="card" style={{ padding: 16, background: 'var(--bg-main)', borderRadius: 8, border: '1px solid var(--border-card)' }}>
                    <h4 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>
                      <Link href={`/blogs/${blog.id}`} style={{ color: 'inherit', textDecoration: 'none' }}>{blog.title}</Link>
                    </h4>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                      {new Date(blog.created_at * 1000).toLocaleDateString()}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', lineHeight: 1.5, whiteSpace: 'pre-wrap', maxHeight: '100px', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                      {blog.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="glass-card-static">
            <h3 className="fb-card-title">Activity Feed</h3>
            
            {profile.current_video && (
              <div className="fb-activity-item">
                <div className="fb-activity-icon">🟢</div>
                <div className="fb-activity-content">
                  <div className="fb-activity-title">
                    {profile.display_name} is studying {profile.current_video.segment_name}
                  </div>
                  <div className="fb-activity-meta">Right now</div>
                  <div style={{ marginTop: 8, padding: 12, background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--primary)' }}>
                    <strong>{profile.current_video.title}</strong>
                  </div>
                </div>
              </div>
            )}

            {profile.enrolled_courses && profile.enrolled_courses.map((course: any) => {
              const pct = course.total_videos > 0 ? (course.completed_videos / course.total_videos * 100) : 0;
              return (
                <div key={course.id} className="fb-activity-item">
                  <div className="fb-activity-icon">{course.icon}</div>
                  <div className="fb-activity-content">
                    <div className="fb-activity-title">
                      {profile.display_name} enrolled in {course.name}
                    </div>
                    <div className="fb-activity-meta">Recently</div>
                    <div style={{ marginTop: 8 }}>
                      <div className="flex-between" style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
                        <span>Course Progress</span>
                        <span>{Math.round(pct)}%</span>
                      </div>
                      <div className="progress-outer" style={{ height: 6 }}>
                        <div className="progress-inner" style={{ width: `${pct}%`, background: 'var(--success)' }} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            
            {(!profile.enrolled_courses || profile.enrolled_courses.length === 0) && !profile.current_video && (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-secondary)' }}>
                No recent activity to show.
              </div>
            )}
            
          </div>
        </div>
      </div>
    </div>
  );
}


function EditProfileModal({ profile, token, onClose, onSave }: { profile: any, token: string, onClose: () => void, onSave: (p: any) => void }) {
  const [formData, setFormData] = useState({
    display_name: profile.display_name || '',
    institute: profile.institute || '',
    bio: profile.bio || '',
    location: profile.location || '',
    work: profile.work || '',
    avatar_url: profile.avatar_url || '',
    cover_url: profile.cover_url || ''
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await profileApi.update(token, formData);
      onSave({ ...profile, ...formData });
      onClose();
    } catch (err) {
      console.error(err);
      alert('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card animate-fade-in" style={{ width: '100%', maxWidth: 500, background: 'var(--bg-card)', padding: 24, borderRadius: 12, maxHeight: '90vh', overflowY: 'auto' }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Edit Profile</h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Display Name</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.display_name} onChange={e => setFormData({...formData, display_name: e.target.value})} required />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Bio</label>
            <textarea className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.bio} onChange={e => setFormData({...formData, bio: e.target.value})} rows={3} placeholder="A short bio..." />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Work</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.work} onChange={e => setFormData({...formData, work: e.target.value})} placeholder="Software Engineer at Acme Corp" />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Education / Institute</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.institute} onChange={e => setFormData({...formData, institute: e.target.value})} placeholder="University Name" />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Location</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} placeholder="San Francisco, CA" />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Avatar Image URL</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.avatar_url} onChange={e => setFormData({...formData, avatar_url: e.target.value})} placeholder="https://..." />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Cover Photo URL</label>
            <input className="input-base" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border-card)', background: 'var(--bg-input)', color: 'var(--text-primary)' }} value={formData.cover_url} onChange={e => setFormData({...formData, cover_url: e.target.value})} placeholder="https://..." />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 16 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Profile'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
