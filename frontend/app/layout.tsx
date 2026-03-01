'use client';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import { Toaster } from 'react-hot-toast';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>BillCheck — Logistics Billing Audit</title>
        <meta name="description" content="Automated logistics billing audit engine. Detect overcharges, raise disputes, recover revenue." />
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
            marginLeft: 240,
            padding: '32px 36px 52px',
            background: 'var(--bg)',
            minHeight: '100vh',
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
