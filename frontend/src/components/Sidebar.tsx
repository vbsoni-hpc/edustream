'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useEffect, useState } from 'react';
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
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Load initial collapsed state
  useEffect(() => {
    const stored = localStorage.getItem('sidebar_collapsed');
    if (stored === 'true') {
      setIsCollapsed(true);
    }
  }, []);

  // Sync collapsed state to body class and local storage
  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(isCollapsed));
    if (isCollapsed) {
      document.body.classList.add('sidebar-collapsed');
    } else {
      document.body.classList.remove('sidebar-collapsed');
    }
  }, [isCollapsed]);

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
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div className="sidebar-logo">🎓 EduStream</div>
          <div className="sidebar-subtitle">Study with your Friends</div>
        </div>
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem', padding: '4px' }}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
            title={isCollapsed ? item.label : undefined}
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span className="sidebar-link-text">{item.label}</span>
          </Link>
        ))}

        {user.username === 'vbsoni' &&
          adminItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
              title={isCollapsed ? item.label : undefined}
            >
              <span className="sidebar-link-icon">{item.icon}</span>
              <span className="sidebar-link-text">{item.label}</span>
            </Link>
          ))}
      </nav>

      <div className="divider"></div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {isCollapsed ? (
          <div 
            onClick={() => setIsCollapsed(false)}
            style={{ fontSize: 20, textAlign: 'center', marginTop: 16, cursor: 'pointer' }}
            title="Messaging"
          >
            💬
          </div>
        ) : (
          <div className="messaging-section">
            <MessagingSection />
          </div>
        )}
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
