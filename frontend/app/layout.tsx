'use client';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import { Toaster } from 'react-hot-toast';
import { useState, useEffect } from 'react';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile]       = useState(false);

  useEffect(() => {
    const handler = (e: CustomEvent) => {
      setSidebarOpen(e.detail.open);
      setIsMobile(e.detail.isMobile);
    };
    window.addEventListener('sidebarToggle', handler as EventListener);
    return () => window.removeEventListener('sidebarToggle', handler as EventListener);
  }, []);

  const marginLeft = isMobile ? 0 : (sidebarOpen ? 240 : 0);
  const paddingTop = isMobile ? '68px' : '32px';

  return (
    <html lang="en">
      <head>
        <title>BillCheck — Logistics Billing Audit</title>
        <meta name="description" content="Automated logistics billing audit engine." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/billcheck-icon.svg" type="image/svg+xml" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          <Sidebar />
          <main style={{
            flex: 1,
            marginLeft,
            paddingTop,
            paddingLeft: isMobile ? 16 : 36,
            paddingRight: isMobile ? 16 : 36,
            paddingBottom: 52,
            background: 'var(--bg)',
            minHeight: '100vh',
            transition: 'margin-left 280ms cubic-bezier(0.16,1,0.3,1)',
          }}>
            {children}
          </main>
        </div>
        <Toaster position="top-right" toastOptions={{
          style: {
            fontFamily: 'var(--font-body)', fontSize: '13px',
            borderRadius: '12px',
            background: 'var(--surface-2)',
            border: '1px solid var(--border-2)',
            color: 'var(--text-primary)',
            boxShadow: 'var(--shadow-md)',
          },
          success: { iconTheme: { primary: '#00C48C', secondary: '#0D1117' } },
          error:   { iconTheme: { primary: '#FF4757', secondary: '#0D1117' } },
        }} />
      </body>
    </html>
  );
}
