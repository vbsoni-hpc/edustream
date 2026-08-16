import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { GlobalPlayerProvider } from './GlobalPlayerContext';
import GlobalPlayer from './GlobalPlayer';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: 'EduStream — Course Platform',
  description: 'Premium EdTech course platform — study with your friends',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <GlobalPlayerProvider>
            <Header />
            {children}
            <GlobalPlayer />
          </GlobalPlayerProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
