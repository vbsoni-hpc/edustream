'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useState, useEffect } from 'react';

const navItems = [
  { href: '/', icon: '🏠', label: 'Dashboard' },
  { href: '/courses', icon: '📚', label: 'My Courses' },
  { href: '/player', icon: '🎬', label: 'Player' },
  { href: '/search', icon: '🔍', label: 'Search' },
  { href: '/friends', icon: '👥', label: 'Friends' },
  { href: '/study-session', icon: '📡', label: 'Study Sessions' },
];

const adminItems = [
  { href: '/admin', icon: '⚙️', label: 'Admin' },
];

export default function Header() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'light';
    setTheme(saved);
  }, []);

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    localStorage.setItem('theme', next);
    document.documentElement.setAttribute('data-theme', next);
  };

  if (!user) return null;

  return (
    <header className="top-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '32px', flex: 1 }}>
        <Link href="/" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary)', letterSpacing: '-0.5px', textDecoration: 'none' }}>
          EduStream
        </Link>
      </div>

      <nav className="header-nav" style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`header-nav-link ${pathname === item.href ? 'active' : ''}`}
            title={item.label}
          >
            {item.icon}
          </Link>
        ))}
        {user.username === 'vbsoni' &&
          adminItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`header-nav-link ${pathname === item.href ? 'active' : ''}`}
              title={item.label}
            >
              {item.icon}
            </Link>
          ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, justifyContent: 'flex-end' }}>
        <button onClick={toggleTheme} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }} title="Toggle Theme">
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', position: 'relative' }} title="Notifications">
          🔔
          <span style={{ position: 'absolute', top: 0, right: -2, width: 8, height: 8, background: 'var(--danger)', borderRadius: '50%' }} />
        </button>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '8px' }}>
          <Link href={`/profile/${user.username}`} style={{ textDecoration: 'none' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '12px' }}>
              {user.display_name?.[0]?.toUpperCase()}
            </div>
          </Link>
          <button onClick={logout} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
