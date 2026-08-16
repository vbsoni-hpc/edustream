'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { usersApi } from './api';

interface User {
  id: number;
  username: string;
  display_name: string;
  is_admin: boolean;
  token: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, userData: Omit<User, 'token'>) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Restore from localStorage
    const storedToken = localStorage.getItem('edustream_token');
    const storedUser = localStorage.getItem('edustream_user');
    if (storedToken && storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        setUser({ ...parsed, token: storedToken });
      } catch {
        localStorage.removeItem('edustream_token');
        localStorage.removeItem('edustream_user');
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((token: string, userData: Omit<User, 'token'>) => {
    const fullUser = { ...userData, token };
    setUser(fullUser);
    localStorage.setItem('edustream_token', token);
    localStorage.setItem('edustream_user', JSON.stringify(userData));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('edustream_token');
    localStorage.removeItem('edustream_user');
  }, []);

  return (
    <AuthContext.Provider value={{ user, token: user?.token || null, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
