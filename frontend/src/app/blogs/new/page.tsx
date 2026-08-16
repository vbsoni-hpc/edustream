"use client";

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { blogsApi } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function NewBlogPage() {
  const { token } = useAuth();
  const router = useRouter();
  
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    if (!title.trim() || !content.trim()) {
      setError("Title and content are required.");
      return;
    }

    try {
      setLoading(true);
      setError('');
      await blogsApi.create(token, title, content);
      router.push('/blogs');
    } catch (err) {
      console.error(err);
      setError("Failed to publish post.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="main-content" style={{ maxWidth: 800 }}>
      <div className="card" style={{ padding: 32, background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border-card)' }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 24 }}>Write a New Post</h1>
        
        {error && (
          <div style={{ padding: 12, background: 'rgba(255,59,48,0.1)', color: 'var(--danger)', borderRadius: 8, marginBottom: 24 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: 'var(--text-secondary)' }}>Title</label>
            <input 
              type="text" 
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Give your post a catchy title..."
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid var(--border-card)',
                background: 'var(--bg-main)',
                color: 'var(--text-primary)',
                fontSize: 18,
                fontWeight: 600
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: 'var(--text-secondary)' }}>Content (Markdown supported)</label>
            <textarea 
              value={content}
              onChange={e => setContent(e.target.value)}
              placeholder="What's on your mind?"
              rows={12}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid var(--border-card)',
                background: 'var(--bg-main)',
                color: 'var(--text-primary)',
                fontSize: 16,
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 16 }}>
            <button 
              type="button" 
              onClick={() => router.push('/blogs')}
              style={{ 
                padding: '12px 24px', 
                borderRadius: 8, 
                border: 'none', 
                background: 'transparent',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={loading}
              style={{ 
                padding: '12px 32px', 
                borderRadius: 8, 
                border: 'none', 
                background: 'var(--primary)', 
                color: 'white',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'Publishing...' : 'Publish Post'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
