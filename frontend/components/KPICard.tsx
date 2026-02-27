'use client';

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'orange' | 'blue' | 'green' | 'red' | 'amber' | 'purple' | 'default';
  icon?: React.ReactNode;
}

const ACCENTS = {
  orange:  { line: '#F57921', glow: 'rgba(245,121,33,0.12)',  val: '#F57921',  icon: 'rgba(245,121,33,0.18)' },
  blue:    { line: '#4E8EFF', glow: 'rgba(78,142,255,0.12)',  val: '#4E8EFF',  icon: 'rgba(78,142,255,0.18)' },
  green:   { line: '#00C48C', glow: 'rgba(0,196,140,0.12)',   val: '#00C48C',  icon: 'rgba(0,196,140,0.18)' },
  red:     { line: '#FF4757', glow: 'rgba(255,71,87,0.12)',   val: '#FF4757',  icon: 'rgba(255,71,87,0.18)' },
  amber:   { line: '#FFB547', glow: 'rgba(255,181,71,0.12)',  val: '#FFB547',  icon: 'rgba(255,181,71,0.18)' },
  purple:  { line: '#7B5CC4', glow: 'rgba(123,92,196,0.12)', val: '#7B5CC4',  icon: 'rgba(123,92,196,0.18)' },
  default: { line: '#2E3558', glow: 'transparent',            val: '#C5CADF',  icon: 'rgba(255,255,255,0.08)' },
};

export default function KPICard({ label, value, sub, accent = 'default', icon }: Props) {
  const a = ACCENTS[accent];
  return (
    <div className="card fade-in" style={{
      padding: '22px 24px',
      overflow: 'hidden',
      position: 'relative',
      borderTop: `2px solid ${a.line}`,
    }}>
      {/* Glow blob */}
      <div style={{
        position: 'absolute', top: -40, right: -40,
        width: 120, height: 120, borderRadius: '50%',
        background: a.glow,
        filter: 'blur(24px)',
        pointerEvents: 'none',
      }}/>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="label" style={{ marginBottom: 12 }}>{label}</div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 28,
            fontWeight: 600,
            lineHeight: 1,
            letterSpacing: '-0.5px',
            color: a.val,
            marginBottom: sub ? 10 : 0,
          }}>{value}</div>
          {sub && (
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>{sub}</div>
          )}
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
