"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { blogsApi } from '@/lib/api';
import Link from 'next/link';

export default function BlogsPage() {
  const { token, user } = useAuth();
  const [blogs, setBlogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'mine'>('all');

  useEffect(() => {
    if (!token) return;

    const fetchBlogs = async () => {
      try {
        setLoading(true);
        let res;
        if (filter === 'mine' && user) {
          res = await blogsApi.getUserBlogs(token, user.username);
        } else {
          res = await blogsApi.getAll(token);
        }
        setBlogs(res.blogs || []);
      } catch (err) {
        console.error("Failed to fetch blogs:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchBlogs();
  }, [token, filter, user]);

  if (!token) return null;

  return (
    <div className="main-content" style={{ maxWidth: 1000 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 32, fontWeight: 800 }}>Edustream Blogs</h1>
        <Link href="/blogs/new" className="btn" style={{ padding: '10px 24px', borderRadius: 8, textDecoration: 'none', background: 'var(--primary)', color: 'white', fontWeight: 600 }}>
          Write a Post
        </Link>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <button 
          onClick={() => setFilter('all')}
          style={{ 
            padding: '8px 16px', 
            borderRadius: 20, 
            border: 'none', 
            background: filter === 'all' ? 'var(--primary)' : 'var(--bg-card)', 
            color: filter === 'all' ? 'white' : 'var(--text-primary)',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          Community Posts
        </button>
        <button 
          onClick={() => setFilter('mine')}
          style={{ 
            padding: '8px 16px', 
            borderRadius: 20, 
            border: 'none', 
            background: filter === 'mine' ? 'var(--primary)' : 'var(--bg-card)', 
            color: filter === 'mine' ? 'white' : 'var(--text-primary)',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          My Posts
        </button>
      </div>

      {loading ? (
        <div>Loading blogs...</div>
      ) : blogs.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', background: 'var(--bg-card)', borderRadius: 12 }}>
          <span style={{ fontSize: 40 }}>📝</span>
          <h3 style={{ marginTop: 16 }}>No posts found</h3>
          <p style={{ color: 'var(--text-secondary)' }}>Be the first to share your thoughts!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {blogs.map(blog => (
            <div key={blog.id} className="card" style={{ padding: 24, background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border-card)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                  {blog.display_name?.[0]?.toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{blog.display_name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    @{blog.username} • {new Date(blog.created_at * 1000).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                {blog.title}
              </h2>
              <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {blog.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
