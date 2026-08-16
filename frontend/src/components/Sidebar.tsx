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
  { href: '/learning', icon: '📊', label: 'My Learning' },
];

const adminItems = [
  { href: '/admin', icon: '⚙️', label: 'Admin' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

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


      {!isCollapsed ? (
        <div style={{ paddingLeft: 16, paddingRight: 16, paddingBottom: 0, paddingTop: 16, flex: 1, overflowY: 'auto', borderTop: '1px solid rgba(255,255,255,0.05)', marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
             {unreadCount > 0 && <span style={{ background: 'var(--danger)', color: 'white', fontSize: 10, padding: '2px 6px', borderRadius: 10, fontWeight: 'bold' }}>{unreadCount} New</span>}
          </div>
          <MessagingSidebar />
        </div>
      ) : (
        <div style={{ padding: '0 16px', flex: 1, marginTop: 16, display: 'flex', justifyContent: 'center' }}>
          <button 
            onClick={() => setIsCollapsed(false)}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem', position: 'relative' }}
            title="Open Inbox"
          >
            <svg style={{width: 24, height: 24}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>
            {unreadCount > 0 && (
              <span style={{
                position: 'absolute', top: -4, right: -4, width: 10, height: 10,
                background: 'var(--danger)', borderRadius: '50%',
                border: '2px solid var(--bg-card)'
              }} />
            )}
          </button>
        </div>
      )}

      <div className="sidebar-user" style={{ marginTop: isCollapsed ? 'auto' : 16 }}>

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
