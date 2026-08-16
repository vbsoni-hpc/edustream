'use client';

import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { messagingApi, usersApi } from '@/lib/api';
import { timeAgo } from '@/lib/utils';

export function MessagingSection() {
  const { token } = useAuth();
  const [openSection, setOpenSection] = useState<'hangout' | 'inbox' | 'dm' | null>(null);
  const [activeDmUser, setActiveDmUser] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    const handleOpenDm = (e: any) => {
      if (e.detail?.id && e.detail?.name) {
        setActiveDmUser({ id: e.detail.id, name: e.detail.name });
        setOpenSection('dm');
        // If sidebar is collapsed, this doesn't automatically open it unless Sidebar listens too
        // We will dispatch a second event for sidebar open if needed, but for now this works when open
      }
    };
    window.addEventListener('open-dm', handleOpenDm);
    return () => window.removeEventListener('open-dm', handleOpenDm);
  }, []);
  
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
          <DMForm token={token} activeUser={activeDmUser} />
        </Accordion>
      </div>
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

function GlobalChat({ token }: { token: string }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [toast, setToast] = useState<{ sender: string, content: string } | null>(null);
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
            const beep = new Audio('data:audio/wav;base64,UklGRmQGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YUAGAACA0PzurlgVAyl4yfnxtWAbAyVwwvXzu2ghBCFou/H0wXAnBh1hs+31x3gtCBparOj1zH80CxdUpOP10Ic6DhVOnd701Y5BERNIldnz2JVIFRJCjtPy3JxPGRE9h83w36JWHRE4gMft4aldIhE0ecHr465kJxIwcrrn5bRrLBMsa7Tk5rlyMRQpZa3g5755NxYmX6bc58OAPBgkWaDY58eGQhsiU5nT5suMSB4gTpPO5s6TTyEfSYzJ5NGZVSUeRYbE4tSeWykeQIC+4NakYS0ePHm53tipZzEfOXOz29mubTYgNm6u2NqydDohM2io1du3ej8jMGOi0du7f0QkLl2czdu+hUonLVmWydrCi08pK1SQxdrFkFQsKlCLwNjHllovKkyFvNfKm18zKkh/t9XMn2U2KkR6stPNpGo6KkF1rdDPqHA+Kz5wqM7PrHVCLDxro8vQsHpHLTpmnsjQtH9LLzhhmcTQt4VQMTZdlMHQuopVMzVZjr3PvY5ZNjRVibnOv5NeOTRShLXNwZdjPDROgLHLw5xoPzRLe6zJxKBtQjRJdqjHxaRxRjVGcqPFxqd2SjZEbZ/Cx6t7TTdCaZq/x65/UTlAZZa8x7GEVTo/YZG5xrOIWjw+Xo22xrWNXj89WoiyxbiRYkE9V4SvxLmVZkQ9VICrwruYa0c9UXunwLycb0o9T3ejv72fc00+TXOfvL6jd1A+S2+bur6me1NASWyXuL6of1dBSGiTtb6rg1pCR2WPsr6th15ERmKLr72vi2JGRV+HrL2xj2ZIRVyDqbyzkmlLRFl/prq0lW1NRVd8orm1mXFQRVV4n7e2nHVTRVN1m7W2nnhWRlFxmLO3oXxZR1BulLG3o4BcSE5rka+3poNfSk1ojay3qIZiS0xliqq2qoplTUxihqe1q41pT0xgg6S0rZBsUUtegKGzrpNvU0tcfJ6yr5ZzVUxaeZuxr5h2WExYdpivsJt5Wk1Xc5WtsJ18XU5VcJKrsJ9/YE9UbY+psKGDY1BTa4ynsKOGZVFSaImlsKWJaFNSZoWir6aLa1VSZIKgrqeOblZRYoCdraiRcVhSYH2brKmTdFpSXnqYq6qVd11SXXeVqaqYel9TW3SSqKuafWFUWnKQpqucf2RUWW+NpKudgmZWWG2KoqqfhWlXWGuHoKqgh2tYV2mFnqmhim5aV2eCnKmjjHBbV2WAmqijj3NdV2R9l6ekkXVfV2J6laalk3hhWGF4k6SllXtjWGB2kKOml31lWV9zjqKmmH9nWl5xi6CmmoJpWl1viZ6lm4RrXFxth5ylnIdtXVxshJulnYlwXlxqgpmknotyX1xogJejn410YVxnfZWioI93Y1xme5OhoJF5ZFxkeZCgoZJ7Zl1jd46foZR9aF1idYyeoZV/al5ic4qcoZeCbF9hcYiboZiEbmBhb4aZoZmGcGFgboSXoJqIcmJgbIKWoJuJdGNga4CUn5yLdmVgan6SnpyNeGZgaXyQnZ2PemdgaHqOnJ2QfGlhZ3iNm52RfmthZnaLmp2Tf2xiZXSJmZ2UgW5jZXOHl52Vg3BkZHGFlp2WhXFkZHCDlZyXh3NlZG+Bk5yYiHVnZG1/kpuYindoZGx+kJuZi3lpZGt8jpqZjXpqZGp6jZmZjnxsZGp5i5iaj35tZWl3iZeakH9vZWh2iJaakoFwZmh0hpWakoNyZ2dzhJOZk4RzaGdyg5KZlIZ1aWdxgZGZlYd2amdwf4+YlYl4a2dvfo6Xlop5bGdufI2Xlot7bWdte4uWlox8bmhseoqVl41+b2hseIiUl46AcWhrd4eTl4+BcmlrdoWSlpCCc2pqdISRlpGEdWpqc4KQlpKFdmtqcoGPlpKGd2xqcYCOlZOIeW1qcX6MlZOJem5qcH2LlJOKe29qb3yKk5SLfXBqbnqIk5SMfnFrbnmHkpSNgHJrbXiGkZSOgXNsbXeFkJSOgnVsbXaDj5SPg3ZtbXWCjpOQhHdubHSBjZOQhnhubHOAjJORh3pvbHJ+i5KRiHtwbHJ9ipKRiXxxbXF8iZGRin1ybXB7h5CRin5zbXB6hpCSi390bnB5hY+RjIF1bm94hI6RjYJ2b293g42RjYN3b292goyRjoR4cG91gYuRjoV5cG91');
            beep.play();
          } catch(e) {}
          
          setToast({ sender: newMessages[newMessages.length - 1].sender_name, content: newMessages[newMessages.length - 1].content });
          setTimeout(() => setToast(null), 4000);
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
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--bg-card)', border: '1px solid var(--primary)',
          padding: '12px 16px', borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 9999,
          maxWidth: 300, animation: 'fadeIn 0.3s ease'
        }}>
          <div style={{ fontSize: 11, color: 'var(--primary-light)', fontWeight: 600, marginBottom: 4 }}>💬 {toast.sender} said:</div>
          <div style={{ fontSize: 13, color: 'white' }}>{toast.content}</div>
        </div>
      )}
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
          <span 
            onClick={() => window.dispatchEvent(new CustomEvent('open-dm', { detail: { id: u.id, name: u.display_name } }))}
            style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '2px 8px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#10b981', fontWeight: 600, cursor: 'pointer' }} 
            title={`DM ${u.display_name}`}
          >
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
