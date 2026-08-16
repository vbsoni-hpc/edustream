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
    <div className="animate-fade-in">
      {/* Profile Header */}
      <div className="profile-header">
        <div className="profile-avatar-large">
          {profile.is_studying && <span className="online-dot-pulse profile-status-dot" />}
          {(profile.display_name || '?')[0].toUpperCase()}
        </div>
        <div className="profile-info">
          <h1 className="profile-name">{profile.display_name}</h1>
          <p className="profile-handle">@{profile.username}</p>
          <p className="profile-status">{statusText}</p>
          {profile.current_video && (
            <div className="profile-studying">
              {profile.current_video.segment_icon} {profile.current_video.segment_name} — {profile.current_video.title}
            </div>
          )}
        </div>
        <div className="profile-actions">
          {friendshipButton()}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="profile-stats-grid">
        <div className="profile-stat-card">
          <div className="profile-stat-value">🔥 {profile.current_streak}</div>
          <div className="profile-stat-label">Day Streak</div>
          <div className="profile-stat-sub">Longest: {profile.longest_streak}d</div>
        </div>
        <div className="profile-stat-card">
          <div className="profile-stat-value">⚡ {profile.total_xp}</div>
          <div className="profile-stat-label">Total XP</div>
          <div className="profile-stat-sub">Level {profile.level}</div>
        </div>
        <div className="profile-stat-card">
          <div className="profile-stat-value">✅ {profile.completed_lectures}</div>
          <div className="profile-stat-label">Lectures Done</div>
        </div>
        <div className="profile-stat-card">
          <div className="profile-stat-value">🎓 {profile.completed_courses}</div>
          <div className="profile-stat-label">Courses Done</div>
        </div>
        <div className="profile-stat-card">
          <div className="profile-stat-value">⏱️ {profile.total_watch_hours}h</div>
          <div className="profile-stat-label">Watch Time</div>
        </div>
        <div className="profile-stat-card">
          <div className="profile-stat-value">📚 {profile.courses_touched}</div>
          <div className="profile-stat-label">Courses Explored</div>
        </div>
      </div>

      {/* XP Progress Bar */}
      <div className="glass-card-static" style={{ marginTop: 24 }}>
        <div className="flex-between" style={{ marginBottom: 8 }}>
          <span style={{ fontWeight: 600 }}>Level {profile.level}</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            {profile.total_xp % 500}/500 XP to Level {profile.level + 1}
          </span>
        </div>
        <div className="progress-outer" style={{ height: 10 }}>
          <div className="progress-inner" style={{ width: `${(profile.total_xp % 500) / 5}%`, background: 'linear-gradient(90deg, var(--primary), #a78bfa)' }} />
        </div>
      </div>

      {/* Enrolled Courses */}
      {profile.enrolled_courses && profile.enrolled_courses.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h4 className="section-title">📚 Currently Learning</h4>
          <div className="carousel">
            {profile.enrolled_courses.map((course: any) => {
              const pct = course.total_videos > 0 ? (course.completed_videos / course.total_videos * 100) : 0;
              return (
                <div key={course.id} className="course-card" style={{ minWidth: 200 }}>
                  <div className="course-card-icon">{course.icon}</div>
                  <div className="course-card-name">{course.name}</div>
                  <div className="course-card-meta">
                    {course.completed_videos}/{course.total_videos} lectures · {Math.round(pct)}%
                  </div>
                  <div className="progress-outer" style={{ marginTop: 8 }}>
                    <div className="progress-inner" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
