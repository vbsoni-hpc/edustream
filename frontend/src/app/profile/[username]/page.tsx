'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { profileApi, friendsApi } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function ProfilePage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    profileApi.get(username).then(p => {
      setProfile(p);
      if (token && p.id !== user?.id) {
        friendsApi.status(token, p.id).then(r => setFriendship(r.friendship)).catch(() => {});
      }
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
      {/* Profile Cover & Header */}
      <div className="fb-profile-header">
        <div className="fb-cover-photo" />
        
        <div className="fb-profile-avatar-wrapper">
          <div className="fb-profile-avatar">
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
          {friendshipButton()}
        </div>
      </div>

      <div className="fb-profile-body">
        {/* Left Column (Sidebar) */}
        <div className="fb-profile-sidebar">
          
          {/* About / Intro */}
          <div className="glass-card-static">
            <h3 className="fb-card-title">Intro</h3>
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
