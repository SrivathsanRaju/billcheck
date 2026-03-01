'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getAlertCount } from '@/lib/api';

const NAV = [
  { href: '/', label: 'Overview',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg> },
  { href: '/upload', label: 'Upload Invoice',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> },
  { href: '/batches', label: 'Batch History',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> },
  { href: '/analytics', label: 'Analytics',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
  { href: '/alerts', label: 'Alerts',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);
  const [open, setOpen]     = useState(false); // always start closed, set properly after mount
  const [isMobile, setIsMobile] = useState(false);
  const [mounted, setMounted]   = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setOpen(!mobile); // open on desktop, closed on mobile
    };
    checkMobile();
    setMounted(true);
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close on mobile when navigating
  useEffect(() => {
    if (isMobile) setOpen(false);
  }, [pathname, isMobile]);

  // Notify layout of sidebar state
  useEffect(() => {
    if (!mounted) return;
    window.dispatchEvent(new CustomEvent('sidebarToggle', { detail: { open, isMobile } }));
  }, [open, isMobile, mounted]);

  useEffect(() => {
    const load = async () => { try { const r = await getAlertCount(); setUnread(r.data.unread || 0); } catch {} };
    load();
    const iv = setInterval(load, 12000);
    return () => clearInterval(iv);
  }, []);

  if (!mounted) return null;

  const toggle = () => setOpen(o => !o);

  return (
    <>
      {/* ── Sidebar panel ── */}
      <div style={{
        position: 'fixed', left: 0, top: 0, bottom: 0, width: 240,
        background: 'linear-gradient(175deg, #2A1F6B 0%, #1E1550 45%, #130E38 100%)',
        display: 'flex', flexDirection: 'column',
        zIndex: 100,
        borderRight: '1px solid rgba(255,255,255,0.07)',
        boxShadow: open ? '6px 0 32px rgba(0,0,0,0.5)' : 'none',
        transform: open ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 280ms cubic-bezier(0.16,1,0.3,1)',
        overflowY: 'auto',
      }}>
        {/* Blobs */}
        <div style={{ position:'absolute', top:-60, left:-60, width:220, height:220, borderRadius:'50%', background:'rgba(245,121,33,0.10)', filter:'blur(50px)', pointerEvents:'none' }}/>
        <div style={{ position:'absolute', bottom:60, right:-80, width:200, height:200, borderRadius:'50%', background:'rgba(71,47,145,0.18)', filter:'blur(60px)', pointerEvents:'none' }}/>

        {/* Logo row — with close button inside on mobile */}
        <div style={{ padding: '20px 16px 18px', borderBottom: '1px solid rgba(255,255,255,0.09)', display:'flex', alignItems:'center', justifyContent:'space-between', gap:8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, flexShrink: 0, background: 'linear-gradient(135deg, #F57921, #F78F45)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 20px rgba(245,121,33,0.50)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="3" width="15" height="13" rx="1.5"/>
                <path d="M16 8h4l3 5v4h-7V8z"/>
                <circle cx="5.5" cy="18.5" r="2.5"/>
                <circle cx="18.5" cy="18.5" r="2.5"/>
              </svg>
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 19, lineHeight: 1, letterSpacing: '-0.4px' }}>
                <span style={{ color: 'white' }}>Bill</span><span style={{ color: '#F57921' }}>Check</span>
              </div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.40)', marginTop: 3, letterSpacing: '0.14em', textTransform: 'uppercase', fontFamily: 'monospace' }}>
                Audit Engine
              </div>
            </div>
          </div>

          {/* ── Hamburger / close button — INSIDE sidebar top-right ── */}
          <button
            onClick={toggle}
            style={{
              width: 36, height: 36, borderRadius: 9, flexShrink: 0,
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.12)',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative',
            }}
          >
            {/* X icon when open */}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Nav label */}
        <div style={{ padding: '16px 22px 8px' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.30)', letterSpacing: '0.14em', textTransform: 'uppercase', fontFamily: 'monospace' }}>
            Main Menu
          </div>
        </div>

        {/* Nav items */}
        <div style={{ flex: 1, padding: '0 12px' }}>
          {NAV.map(item => {
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} style={{ textDecoration: 'none', display: 'block', marginBottom: 5 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '11px 15px', borderRadius: 11,
                  background: active ? 'linear-gradient(135deg, #F57921, #F78F45)' : 'rgba(255,255,255,0.055)',
                  boxShadow: active ? '0 4px 18px rgba(245,121,33,0.40)' : 'none',
                  border: active ? 'none' : '1px solid rgba(255,255,255,0.08)',
                  transition: 'all 160ms cubic-bezier(0.16,1,0.3,1)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ color: active ? 'white' : 'rgba(255,255,255,0.65)', flexShrink: 0 }}>{item.icon}</div>
                    <span style={{ fontSize: 14, fontWeight: active ? 700 : 500, color: active ? 'white' : 'rgba(255,255,255,0.80)' }}>
                      {item.label}
                    </span>
                  </div>
                  {item.label === 'Alerts' && unread > 0 && (
                    <span style={{ background: active ? 'rgba(255,255,255,0.28)' : '#FF4757', color: 'white', borderRadius: 20, fontSize: 11, fontWeight: 700, padding: '3px 8px', flexShrink: 0, fontFamily: 'monospace' }}>
                      {unread > 99 ? '99+' : unread}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>

        <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '8px 20px' }}/>

        {/* Footer */}
        <div style={{ padding: '12px 14px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', background: 'rgba(0,196,140,0.10)', borderRadius: 11, border: '1px solid rgba(0,196,140,0.22)', marginBottom: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#00C48C', boxShadow: '0 0 10px #00C48C', flexShrink: 0 }}/>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#00C48C', lineHeight: 1.3 }}>All systems operational</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.30)', marginTop: 2, fontFamily: 'monospace' }}>v1.0.0 · Audit Engine</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.22)', fontFamily: 'monospace' }}>BillCheck © 2025</span>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#F57921', background: 'rgba(245,121,33,0.15)', border: '1px solid rgba(245,121,33,0.30)', padding: '3px 8px', borderRadius: 5, fontFamily: 'monospace' }}>BETA</span>
          </div>
        </div>
      </div>

      {/* ── Floating hamburger — only visible when sidebar is CLOSED ── */}
      <button
        onClick={toggle}
        style={{
          position: 'fixed',
          top: 16, left: 16,
          zIndex: 200,
          width: 44, height: 44,
          borderRadius: 12,
          background: 'linear-gradient(135deg, #F57921, #F78F45)',
          border: 'none',
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(245,121,33,0.5)',
          opacity: open ? 0 : 1,
          pointerEvents: open ? 'none' : 'all',
          transition: 'opacity 200ms ease',
        }}
        aria-label="Open menu"
      >
        {/* Three lines */}
        <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
          <span style={{ display:'block', width:20, height:2, borderRadius:2, background:'white' }}/>
          <span style={{ display:'block', width:14, height:2, borderRadius:2, background:'white' }}/>
          <span style={{ display:'block', width:20, height:2, borderRadius:2, background:'white' }}/>
        </div>
        {/* Unread dot */}
        {unread > 0 && (
          <span style={{ position:'absolute', top:8, right:8, width:9, height:9, borderRadius:'50%', background:'#FF4757', border:'2px solid #0D0F1A' }}/>
        )}
      </button>

      {/* ── Dark overlay — tap anywhere to close on mobile ── */}
      {isMobile && (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.65)',
            backdropFilter: 'blur(3px)',
            zIndex: 99,
            opacity: open ? 1 : 0,
            pointerEvents: open ? 'all' : 'none',
            transition: 'opacity 240ms ease',
          }}
        />
      )}
    </>
  );
}
