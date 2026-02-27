'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getAlertCount } from '@/lib/api';

const NAV = [
  { href: '/', label: 'Overview',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg> },
  { href: '/upload', label: 'Upload Invoice',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> },
  { href: '/batches', label: 'Batch History',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> },
  { href: '/analytics', label: 'Analytics',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
  { href: '/alerts', label: 'Alerts',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const load = async () => { try { const r = await getAlertCount(); setUnread(r.data.unread || 0); } catch {} };
    load();
    const iv = setInterval(load, 12000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div style={{
      position: 'fixed', left: 0, top: 0, bottom: 0, width: 230,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      zIndex: 50,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <Link href="/" style={{ textDecoration: 'none', display: 'block' }}>
          <img
            src="/billcheck-logo.svg"
            alt="BillCheck"
            style={{ height: 46, width: 'auto', display: 'block' }}
          />
        </Link>
      </div>

      {/* Nav label */}
      <div style={{ padding: '16px 20px 8px' }}>
        <div className="label">Navigation</div>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, padding: '0 10px', overflowY: 'auto' }}>
        {NAV.map(item => {
          const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href} style={{ textDecoration: 'none', display: 'block', marginBottom: 3 }}>
              <div
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '9px 12px', borderRadius: 10,
                  background: active ? 'var(--grad-blue)' : 'transparent',
                  boxShadow: active ? 'var(--shadow-blue)' : 'none',
                  transition: 'all var(--dur) var(--ease)', cursor: 'pointer',
                }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-2)'; }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ color: active ? 'white' : 'var(--text-muted)', transition: 'color var(--dur) var(--ease)', flexShrink: 0 }}>
                    {item.icon}
                  </div>
                  <span style={{
                    fontSize: 13.5, fontWeight: active ? 700 : 500,
                    color: active ? 'white' : 'var(--text-secondary)',
                    transition: 'color var(--dur) var(--ease)',
                  }}>
                    {item.label}
                  </span>
                </div>
                {item.label === 'Alerts' && unread > 0 && (
                  <span style={{
                    background: active ? 'rgba(255,255,255,0.2)' : 'var(--red)',
                    color: 'white', borderRadius: 20,
                    fontSize: 10, fontWeight: 700, padding: '2px 7px', flexShrink: 0,
                    fontFamily: 'var(--font-mono)',
                  }}>{unread > 99 ? '99+' : unread}</span>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--green-light)', borderRadius: 10, border: '1px solid rgba(0,196,140,0.15)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 8px var(--green)', flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--green)' }}>All systems operational</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1, fontFamily: 'var(--font-mono)' }}>v1.0.0</div>
          </div>
        </div>
      </div>
    </div>
  );
}
