'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useEffect } from 'react';
import { usersApi } from '@/lib/api';
import { MessagingSection } from '@/components/MessagingSidebar';

const navItems = [
  { href: '/', icon: '🏠', label: 'Dashboard' },
  { href: '/courses', icon: '📚', label: 'My Courses' },
  { href: '/player', icon: '🎬', label: 'Player' },
  { href: '/learning', icon: '📊', label: 'My Learning' },
];

const adminItems = [
  { href: '/admin', icon: '⚙️', label: 'Admin' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Heartbeat ping
  useEffect(() => {
    if (!user?.token) return;
    const ping = () => usersApi.ping(user.token).catch(() => {});
    ping();
    const interval = setInterval(ping, 60000);
    return () => clearInterval(interval);
  }, [user?.token]);

  if (!user) return null;

  const initial = (user.display_name || user.username || '?')[0].toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">🎓 EduStream</div>
      <div className="sidebar-subtitle">Study with your Friends</div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}

        {user.username === 'vbsoni' &&
          adminItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
            >
              <span className="sidebar-link-icon">{item.icon}</span>
              {item.label}
            </Link>
          ))}
      </nav>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <MessagingSection />
      </div>

      <div className="sidebar-user" style={{ marginTop: 'auto' }}>
        <div className="sidebar-user-info">
          <div className="sidebar-avatar">{initial}</div>
          <div>
            <div className="sidebar-user-name">{user.display_name}</div>
            <div className="sidebar-user-handle">@{user.username}</div>
          </div>
        </div>
        <button className="btn btn-danger btn-sm btn-full" onClick={logout}>
          Logout
        </button>
      </div>
    </aside>
  );
}
