'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useEffect, useState } from 'react';
import { usersApi, messagingApi } from '@/lib/api';
import MessagingSidebar from './MessagingSidebar';


const navItems = [
  { href: '/', icon: '🏠', label: 'Dashboard' },
  { href: '/courses', icon: '📚', label: 'My Courses' },
  { href: '/player', icon: '🎬', label: 'Player' },
  { href: '/friends', icon: '👥', label: 'Friends' },
  { href: '/study-session', icon: '📡', label: 'Study Sessions' },
];

const adminItems = [
  { href: '/admin', icon: '⚙️', label: 'Admin' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'light';
    setTheme(saved);
    document.documentElement.setAttribute('data-theme', saved);
  }, []);

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    localStorage.setItem('theme', next);
    document.documentElement.setAttribute('data-theme', next);
  };

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

  // Listen for open-dm event to automatically expand the sidebar
  useEffect(() => {
    const handleOpenDm = () => setIsCollapsed(false);
    window.addEventListener('open-dm', handleOpenDm);
    return () => window.removeEventListener('open-dm', handleOpenDm);
  }, []);

  // Heartbeat ping and Unread Check
  useEffect(() => {
    if (!user?.token) return;
    const ping = () => {
      usersApi.ping(user.token).catch(() => {});
      messagingApi.getUnread(user.token).then(res => setUnreadCount(res.messages?.length || 0)).catch(() => {});
    };
    ping();
    const interval = setInterval(ping, 15000);
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


      <div className="sidebar-user" style={{ marginTop: isCollapsed ? 'auto' : 16 }}>


        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={toggleTheme} style={{ flex: 1, padding: '6px 4px' }} title="Toggle Theme">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <button className="btn btn-danger btn-sm" onClick={logout} style={{ flex: 3 }}>
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
