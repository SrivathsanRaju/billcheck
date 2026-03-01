import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: 'BillCheck — Logistics Billing Audit',
  description: 'Automated logistics billing audit engine. Detect overcharges, raise disputes, recover revenue.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/billcheck-icon.svg" type="image/svg+xml" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <Sidebar />
        <main id="main-content" style={{
          marginLeft: 240,
          padding: '32px 36px 52px',
          background: 'var(--bg)',
          minHeight: '100vh',
          transition: 'margin-left 280ms cubic-bezier(0.16,1,0.3,1)',
        }}>
          {children}
        </main>
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
