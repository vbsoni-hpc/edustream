'use client';

import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { messagingApi, usersApi } from '@/lib/api';
import { timeAgo } from '@/lib/utils';

export default function MessagingSidebar() {
  const { token, user } = useAuth();
  const [openSection, setOpenSection] = useState<'inbox' | 'dm' | null>(null);
  const [activeDmUser, setActiveDmUser] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    const handleOpenDm = (e: any) => {
      if (e.detail?.id && e.detail?.name) {
        setActiveDmUser({ id: e.detail.id, name: e.detail.name });
        setOpenSection('dm');
      }
    };
    window.addEventListener('open-dm', handleOpenDm);
    return () => window.removeEventListener('open-dm', handleOpenDm);
  }, []);

  if (!token || !user) return null;

  return (
    <div style={{ marginTop: 20 }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>Online</h3>
      <OnlineUsers token={token} />

      <div className="divider" style={{ margin: '16px 0', borderColor: 'var(--border-card)' }} />

      <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>Messaging</h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Accordion
          title="📥 Inbox"
          isOpen={openSection === 'inbox'}
          onClick={() => setOpenSection(openSection === 'inbox' ? null : 'inbox')}
        >
          <Inbox token={token} />
        </Accordion>

        <Accordion
          title="🖍️ DM"
          isOpen={openSection === 'dm'}
          onClick={() => setOpenSection(openSection === 'dm' ? null : 'dm')}
        >
          <DMForm token={token} activeUser={activeDmUser} />
        </Accordion>
      </div>
    </div>
  );
}

function OnlineUsers({ token }: { token: string }) {
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await usersApi.getOnline();
        setUsers(res.users);
      } catch (e) {
        console.error(e);
      }
    };
    fetchUsers();
    const interval = setInterval(fetchUsers, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {users.map((u, i) => (
        <div key={u.id ?? i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            onClick={() => window.dispatchEvent(new CustomEvent('open-dm', { detail: { id: u.id, name: u.display_name } }))}
            style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '2px 8px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#10b981', fontWeight: 600, cursor: 'pointer' }}
            title={`DM ${u.display_name}`}
          >
            <span className="online-dot" style={{ width: 6, height: 6, margin: 0, background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            {u.display_name}
          </span>
          {!!u.is_admin && <span className="badge badge-success" style={{ fontSize: 9, padding: '2px 4px' }}>Admin</span>}
        </div>
      ))}
      {users.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No users online.</div>}
    </div>
  );
}

function Inbox({ token }: { token: string }) {
  const [messages, setMessages] = useState<any[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastMessageIdRef = useRef<number | null>(null);

  useEffect(() => {
    // Create audio context only once
    audioRef.current = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
  }, []);

  useEffect(() => {
    const fetchInbox = async () => {
      try {
        const res = await messagingApi.getInbox(token);
        // Reverse to show newest at bottom!
        const newMessages = res.messages.reverse();
        
        if (newMessages.length > 0) {
            const latestId = newMessages[newMessages.length - 1].id;
            // play sound if we have new unread messages
            if (lastMessageIdRef.current !== null && latestId > lastMessageIdRef.current) {
               if (audioRef.current) {
                  audioRef.current.play().catch(() => {});
               }
            }
            lastMessageIdRef.current = latestId;
        }

        setMessages(newMessages);
      } catch (e) {
        console.error(e);
      }
    };
    fetchInbox();
    const interval = setInterval(fetchInbox, 10000);
    return () => clearInterval(interval);
  }, [token]);

  // Scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={{ maxHeight: 300, overflowY: 'auto', paddingRight: 4, display: 'flex', flexDirection: 'column' }}>
      {messages.map((m, i) => (
        <div key={m.id ?? i} style={{ background: 'var(--bg-card)', padding: '8px', borderRadius: 8, fontSize: 12, marginBottom: 8, borderLeft: !m.is_read ? '2px solid var(--primary)' : 'none' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <strong style={{ color: 'var(--text-primary)' }}>{m.sender_name}</strong>
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{timeAgo(m.created_at)}</span>
          </div>
          <div style={{ wordBreak: 'break-word', lineHeight: 1.4, color: 'var(--text-secondary)' }}>{m.content}</div>
        </div>
      ))}
      {messages.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Inbox is empty.</div>}
      <div ref={endRef} />
    </div>
  );
}

function DMForm({ token, activeUser }: { token: string, activeUser: { id: number, name: string } | null }) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => { setSuccess(false); }, [activeUser]);

  if (!activeUser) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>Click an online user above to send a DM.</div>;
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setLoading(true);
    try {
      await messagingApi.sendDM(token, activeUser.id, content);
      setContent('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 12, color: 'var(--primary-light)', fontWeight: 600 }}>
        To: {activeUser.name}
      </div>
      {success && <div style={{ fontSize: 11, color: 'var(--success)' }}>Message sent!</div>}
      <form onSubmit={handleSend} style={{ display: 'flex', gap: 6, flexDirection: 'column' }}>
        <textarea
          className="input"
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Type your message..."
          style={{ fontSize: 12, padding: '6px 8px', minHeight: 60, resize: 'none' }}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={loading || !content.trim()} style={{ fontSize: 12 }}>
          Send DM
        </button>
      </form>
    </div>
  );
}

function Accordion({ title, isOpen, onClick, children }: { title: string, isOpen: boolean, onClick: () => void, children: React.ReactNode }) {
  return (
    <div style={{ border: '1px solid var(--border-card)', borderRadius: 8, overflow: 'hidden' }}>
      <div
        onClick={onClick}
        style={{
          padding: '10px 12px', background: 'var(--bg-card)', cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)'
        }}
      >
        <span>{isOpen ? '⌄' : '›'} {title}</span>
      </div>
      <div style={{ padding: 12, background: 'rgba(26,29,41,0.4)', display: isOpen ? 'block' : 'none' }}>
        {children}
      </div>
    </div>
  );
}
