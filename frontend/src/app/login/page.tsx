'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { authApi } from '@/lib/api';

export default function LoginPage() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [institute, setInstitute] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace('/');
    }
  }, [user, router]);

  // Redirect if already logged in
  if (user) {
    return null;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.login(username, password);
      login(res.token, {
        id: res.user_id,
        username: res.username,
        display_name: res.display_name,
        is_admin: res.is_admin,
      });
      router.replace('/');
    } catch (err: any) {
      setError(err.message || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Username and password are required');
      return;
    }
    if (password !== confirmPass) {
      setError("Passwords don't match");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register(username, password, displayName || username, institute);
      login(res.token, {
        id: res.user_id,
        username: res.username,
        display_name: displayName || username,
        is_admin: false,
      });
      router.replace('/');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fb-login-wrapper">
      <div className="fb-login-container">
        <div className="fb-login-left">
          <h1 className="fb-login-logo">EduStream</h1>
          <h2 className="fb-login-subtitle">Study with your friends and connect with learners around the globe.</h2>
        </div>
        <div className="fb-login-right">
          <div className="fb-login-card">
            {tab === 'login' ? (
              <form onSubmit={handleLogin} className="fb-form">
                <input
                  className="fb-input"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                  autoComplete="username"
                />
                <input
                  className="fb-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete="current-password"
                />
                {error && <div className="form-error" style={{ textAlign: 'center', marginBottom: 16 }}>{error}</div>}
                <button className="fb-btn fb-btn-primary" type="submit" disabled={loading}>
                  {loading ? 'Logging in...' : 'Log In'}
                </button>
                <div className="fb-divider"></div>
                <div style={{ textAlign: 'center' }}>
                  <button type="button" className="fb-btn fb-btn-success" onClick={() => { setTab('register'); setError(''); }}>
                    Create new account
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="fb-form">
                <input
                  className="fb-input"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Choose a username"
                  autoComplete="username"
                />
                <input
                  className="fb-input"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Display Name"
                />
                <input
                  className="fb-input"
                  type="text"
                  value={institute}
                  onChange={(e) => setInstitute(e.target.value)}
                  placeholder="Institute / School"
                />
                <input
                  className="fb-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="New password"
                  autoComplete="new-password"
                />
                <input
                  className="fb-input"
                  type="password"
                  value={confirmPass}
                  onChange={(e) => setConfirmPass(e.target.value)}
                  placeholder="Confirm password"
                  autoComplete="new-password"
                />
                {error && <div className="form-error" style={{ textAlign: 'center', marginBottom: 16 }}>{error}</div>}
                <button className="fb-btn fb-btn-success" type="submit" disabled={loading}>
                  {loading ? 'Signing Up...' : 'Sign Up'}
                </button>
                <div className="fb-divider"></div>
                <div style={{ textAlign: 'center' }}>
                  <button type="button" className="fb-btn fb-btn-secondary" onClick={() => { setTab('login'); setError(''); }}>
                    Already have an account?
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
