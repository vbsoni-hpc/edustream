'use client';

import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { messagingApi } from '@/lib/api';
import { timeAgo } from '@/lib/utils';

export function FloatingChat() {
  const { token, user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadGlobal, setUnreadGlobal] = useState(false);
  const lastIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!token || isOpen) {
       setUnreadGlobal(false);
       return;
    }
    const checkUnread = async () => {
      try {
        const res = await messagingApi.getGroupMessages();
        const msgs = res.messages.reverse();
        if (msgs.length > 0) {
          const latestId = msgs[msgs.length - 1].id;
          if (lastIdRef.current !== null && latestId > lastIdRef.current) {
            setUnreadGlobal(true);
          }
          lastIdRef.current = latestId;
        }
      } catch (e) {}
    };
    const interval = setInterval(checkUnread, 10000);
    return () => clearInterval(interval);
  }, [token, isOpen]);

  if (!token || !user) return null;

  return (
    <>
      <button
        className="floating-chat-button"
        onClick={() => { setIsOpen(!isOpen); setUnreadGlobal(false); }}
        title="Chat & Hangout"
        style={{ position: 'relative' }}
      >
        {isOpen ? '✕' : '💬'}
        {!isOpen && unreadGlobal && (
          <span style={{
            position: 'absolute', top: -2, right: -2, width: 12, height: 12,
            background: 'var(--danger)', borderRadius: '50%',
            border: '2px solid var(--bg-card)'
          }} />
        )}
      </button>

      {isOpen && (
        <div className="floating-chat-widget">
          <div className="floating-chat-header">
            EduStream Hangout
          </div>
          <div className="floating-chat-body">
            <GlobalChat token={token} user={user} />
          </div>
        </div>
      )}
    </>
  );
}

function GlobalChat({ token, user }: { token: string, user: any }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const lastMessageIdRef = useRef<number | null>(null);
  const [toast, setToast] = useState<{ sender: string, content: string } | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setIsMuted(localStorage.getItem('chat_muted') === 'true');
    audioRef.current = new Audio('data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjYwLjE2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWgAAAAAAMAAAAAAB54AAB/4gAAAAAAAAC1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABaAAAAAAAwAAAAAAHngAAH/iAAAAAAAAAA=');
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

        if (!isInitialLoad && lastMessageIdRef.current !== null && latestId > lastMessageIdRef.current && !isMuted) {
          if (audioRef.current) {
            audioRef.current.play().catch(() => {});
          }

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {toast && (
        <div className="toast-notification">
          <div style={{ fontSize: 11, color: 'var(--primary-light)', fontWeight: 600, marginBottom: 4 }}>💬 {toast.sender} said:</div>
          <div style={{ fontSize: 13, color: 'white' }}>{toast.content}</div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: 4 }}>
        <button
          onClick={toggleMute}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
          title={isMuted ? "Unmute Notifications" : "Mute Notifications"}
        >
          {isMuted ? '🔕' : '🔔'}
        </button>
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8, fontStyle: 'italic' }}>
        🤖 Chat is monitored by AI Moderator.
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 8, marginBottom: 8 }}>
        {messages.map(m => {
          const isMe = m.sender_name === user.display_name || m.sender_username === user.username;
          return (
            <div key={m.id} className={`chat-message ${isMe ? 'outgoing' : 'incoming'}`}>
              {!isMe && <div className="chat-sender">{m.sender_name}</div>}
              <div className="chat-bubble">
                {m.content}
              </div>
              <div className="chat-time">{timeAgo(m.created_at)}</div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: 6, padding: '4px 0' }}>
        <input
          className="input"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Message..."
          style={{ flex: 1, fontSize: 13, padding: '8px 12px', borderRadius: 20 }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()} style={{ borderRadius: 20, padding: '8px 16px' }}>Send</button>
      </form>
    </div>
  );
}
