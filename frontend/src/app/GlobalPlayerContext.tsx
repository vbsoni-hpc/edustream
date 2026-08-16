'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';

type GlobalPlayerContextType = {
  videoId: number;
  setVideoId: (id: number) => void;
  isPiP: boolean;
  setIsPiP: (val: boolean) => void;
};

const GlobalPlayerContext = createContext<GlobalPlayerContextType | undefined>(undefined);

export function GlobalPlayerProvider({ children }: { children: React.ReactNode }) {
  const [videoId, setVideoIdState] = useState<number>(0);
  const [isPiP, setIsPiP] = useState<boolean>(false);
  const pathname = usePathname();

  useEffect(() => {
    // Load initial videoId from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('current_video_id');
      if (stored) {
        setVideoIdState(parseInt(stored, 10));
      }
    }
  }, []);

  useEffect(() => {
    if (pathname === '/player') {
      setIsPiP(false);
    } else {
      // Auto PiP when leaving /player
      if (videoId > 0) {
        setIsPiP(true);
      }
    }
  }, [pathname, videoId]);

  const setVideoId = (id: number) => {
    setVideoIdState(id);
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_video_id', String(id));
    }
    if (pathname !== '/player') {
      setIsPiP(true);
    }
  };

  return (
    <GlobalPlayerContext.Provider value={{ videoId, setVideoId, isPiP, setIsPiP }}>
      {children}
    </GlobalPlayerContext.Provider>
  );
}

export function useGlobalPlayer() {
  const context = useContext(GlobalPlayerContext);
  if (context === undefined) {
    throw new Error('useGlobalPlayer must be used within a GlobalPlayerProvider');
  }
  return context;
}
