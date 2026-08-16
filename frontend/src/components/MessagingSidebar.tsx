'use client';

import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { messagingApi, usersApi } from '@/lib/api';
import { timeAgo } from '@/lib/utils';

export function MessagingSection() {
  const { token } = useAuth();
  const [openSection, setOpenSection] = useState<'hangout' | 'inbox' | 'dm' | null>(null);
  
  if (!token) return null;

  return (
    <div className="messaging-section" style={{ marginTop: 12, padding: '0 8px' }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>Online</h3>
      <OnlineUsers token={token} />
      
      <div className="divider" style={{ margin: '16px 0', borderColor: 'var(--border-card)' }} />

      <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>Messaging</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Accordion 
          title="💬 Hangout" 
          isOpen={openSection === 'hangout'} 
          onClick={() => setOpenSection(openSection === 'hangout' ? null : 'hangout')}
        >
          <GlobalChat token={token} />
        </Accordion>
        
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
          <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>
            Click an online user above to send a DM.
          </div>
        </Accordion>
      </div>
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
      {isOpen && (
        <div style={{ padding: 12, background: 'rgba(26,29,41,0.4)' }}>
          {children}
        </div>
      )}
    </div>
  );
}

function GlobalChat({ token }: { token: string }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);
  const lastMessageIdRef = useRef<number | null>(null);

  useEffect(() => {
    const storedMute = localStorage.getItem('chat_muted');
    if (storedMute !== null) {
      setIsMuted(storedMute === 'true');
    }
  }, []);

  const toggleMute = () => {
    const newMute = !isMuted;
    setIsMuted(newMute);
    localStorage.setItem('chat_muted', String(newMute));
  };

  const fetchMessages = async () => {
    try {
      const res = await messagingApi.getGroupMessages();
      const newMessages = res.messages.reverse();
      
      if (newMessages.length > 0) {
        const latestId = newMessages[newMessages.length - 1].id;
        
        // Play sound if there's a new message, it's not the initial load, and we're not muted
        if (!isInitialLoad && lastMessageIdRef.current !== null && latestId > lastMessageIdRef.current && !isMuted) {
          try {
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            gain.gain.setValueAtTime(0.1, ctx.currentTime);
            osc.start();
            gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 0.1);
            osc.stop(ctx.currentTime + 0.1);
          } catch(e) {}
        }
        
        lastMessageIdRef.current = latestId;
      }
      
      setMessages(newMessages);
      if (isInitialLoad) setIsInitialLoad(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchMessages();
    const interval = setInterval(fetchMessages, 5000);
    return () => clearInterval(interval);
  }, [isMuted, isInitialLoad]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setLoading(true);
    try {
      await messagingApi.sendGroupMessage(token, input);
      setInput('');
      await fetchMessages();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 300 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
        <button 
          onClick={toggleMute} 
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
          title={isMuted ? "Unmute Notifications" : "Mute Notifications"}
        >
          {isMuted ? '🔕' : '🔔'}
        </button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingRight: 4, marginBottom: 8 }}>
        {messages.map(m => (
          <div key={m.id} style={{ background: 'var(--bg-card)', padding: '8px', borderRadius: 8, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <strong style={{ color: 'var(--primary-light)' }}>{m.sender_name}</strong>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{timeAgo(m.created_at)}</span>
            </div>
            <div style={{ wordBreak: 'break-word', lineHeight: 1.4 }}>{m.content}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={handleSend} style={{ display: 'flex', gap: 6 }}>
        <input 
          className="input" 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          placeholder="Type..." 
          style={{ flex: 1, fontSize: 12, padding: '6px 8px' }}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={loading || !input.trim()} style={{ padding: '6px 10px', fontSize: 12 }}>Send</button>
      </form>
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
          <span style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '2px 8px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#10b981', fontWeight: 600, cursor: 'pointer' }} title={`DM ${u.display_name}`}>
            <span className="online-dot" style={{ width: 6, height: 6, margin: 0, background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            {u.display_name}
          </span>
          {u.is_admin && <span className="badge badge-success" style={{ fontSize: 9, padding: '2px 4px' }}>Admin</span>}
        </div>
      ))}
      {users.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No users online.</div>}
    </div>
  );
}

function Inbox({ token }: { token: string }) {
  const [messages, setMessages] = useState<any[]>([]);
  
  useEffect(() => {
    const fetchInbox = async () => {
      try {
        const res = await messagingApi.getInbox(token);
        setMessages(res.messages);
      } catch (e) {
        console.error(e);
      }
    };
    fetchInbox();
  }, [token]);

  return (
    <div style={{ maxHeight: 300, overflowY: 'auto', paddingRight: 4 }}>
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
    </div>
  );
}
