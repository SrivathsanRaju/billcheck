'use client';
import { useEffect, useRef, useState } from 'react';

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'orange' | 'blue' | 'green' | 'red' | 'amber' | 'purple' | 'default';
  icon?: React.ReactNode;
  trend?: number; // positive = up (bad for overcharge, good for invoices)
  trendLabel?: string;
}

const ACCENTS = {
  orange:  { line: '#F57921', glow: 'rgba(245,121,33,0.14)',  val: '#F57921',  icon: 'rgba(245,121,33,0.18)' },
  blue:    { line: '#4E8EFF', glow: 'rgba(78,142,255,0.14)',  val: '#4E8EFF',  icon: 'rgba(78,142,255,0.18)' },
  green:   { line: '#00C48C', glow: 'rgba(0,196,140,0.14)',   val: '#00C48C',  icon: 'rgba(0,196,140,0.18)' },
  red:     { line: '#FF4757', glow: 'rgba(255,71,87,0.14)',   val: '#FF4757',  icon: 'rgba(255,71,87,0.18)' },
  amber:   { line: '#FFB547', glow: 'rgba(255,181,71,0.14)',  val: '#FFB547',  icon: 'rgba(255,181,71,0.18)' },
  purple:  { line: '#7B5CC4', glow: 'rgba(123,92,196,0.14)', val: '#7B5CC4',  icon: 'rgba(123,92,196,0.18)' },
  default: { line: '#2E3558', glow: 'transparent',            val: '#C5CADF',  icon: 'rgba(255,255,255,0.08)' },
};

function useCountUp(target: number, duration = 900): number {
  const [current, setCurrent] = useState(0);
  const raf = useRef<number | null>(null);
  const start = useRef<number | null>(null);
  const from = useRef(0);

  useEffect(() => {
    if (target === 0) { setCurrent(0); return; }
    from.current = current;
    start.current = null;
    const animate = (ts: number) => {
      if (!start.current) start.current = ts;
      const progress = Math.min((ts - start.current) / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(from.current + (target - from.current) * eased));
      if (progress < 1) raf.current = requestAnimationFrame(animate);
    };
    raf.current = requestAnimationFrame(animate);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  return current;
}

export default function KPICard({ label, value, sub, accent = 'default', icon, trend, trendLabel }: Props) {
  const a = ACCENTS[accent];

  // Animate numeric values
  const isNumeric = typeof value === 'number';
  const animated = useCountUp(isNumeric ? value : 0);

  // For INR strings like "₹1,23,456" — extract and animate the number
  const isINR = typeof value === 'string' && value.startsWith('₹');
  const inrNum = isINR ? parseFloat(value.replace(/[₹,]/g, '')) : 0;
  const animatedINR = useCountUp(isINR ? inrNum : 0);

  // For percent strings like "12.3%"
  const isPct = typeof value === 'string' && value.endsWith('%');
  const pctNum = isPct ? parseFloat(value) : 0;
  const animatedPct = useCountUp(isPct ? Math.round(pctNum * 10) : 0);

  function displayValue() {
    if (isNumeric) return animated.toLocaleString('en-IN');
    if (isINR) {
      const n = animatedINR;
      if (n >= 10_00_000) return `₹${(n / 10_00_000).toFixed(2)}L`;
      if (n >= 1_000) return `₹${(n / 1_000).toFixed(1)}K`;
      return `₹${n.toLocaleString('en-IN')}`;
    }
    if (isPct) return `${(animatedPct / 10).toFixed(1)}%`;
    return value;
  }

  return (
    <div className="card fade-in" style={{
      padding: '22px 24px',
      overflow: 'hidden',
      position: 'relative',
      borderTop: `2px solid ${a.line}`,
      cursor: 'default',
      transition: 'transform 0.18s ease, box-shadow 0.18s ease',
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
      (e.currentTarget as HTMLElement).style.boxShadow = `0 8px 32px rgba(0,0,0,0.3), 0 0 0 1px ${a.line}33`;
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLElement).style.transform = '';
      (e.currentTarget as HTMLElement).style.boxShadow = '';
    }}
    >
      {/* Glow blob */}
      <div style={{
        position: 'absolute', top: -40, right: -40,
        width: 130, height: 130, borderRadius: '50%',
        background: a.glow,
        filter: 'blur(28px)',
        pointerEvents: 'none',
      }}/>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="label" style={{ marginBottom: 12, letterSpacing: '0.08em', fontSize: 10 }}>{label}</div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 28,
            fontWeight: 600,
            lineHeight: 1,
            letterSpacing: '-0.5px',
            color: a.val,
            marginBottom: sub ? 10 : 0,
            transition: 'color 0.3s ease',
          }}>{displayValue()}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            {sub && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>{sub}</div>
            )}
            {trend !== undefined && trend !== 0 && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 2,
                fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 600,
                color: trend > 0 ? 'var(--red)' : 'var(--green)',
                background: trend > 0 ? 'rgba(255,71,87,0.1)' : 'rgba(0,196,140,0.1)',
                padding: '1px 5px', borderRadius: 3,
              }}>
                {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
                {trendLabel && <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}> {trendLabel}</span>}
              </div>
            )}
          </div>
        </div>
        {icon && (
          <div style={{
            width: 44, height: 44,
            borderRadius: 12,
            flexShrink: 0,
            background: a.icon,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginLeft: 14,
            color: a.val,
          }}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
