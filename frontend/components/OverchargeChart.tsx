'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { formatINR } from '@/lib/api';

interface Props { data: Array<{ name: string; overcharge: number }>; title?: string; subtitle?: string; }

const Tip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border-2)', borderRadius: 10, padding: '10px 14px', fontSize: 12, boxShadow: 'var(--shadow-md)' }}>
      <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--orange)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{formatINR(payload[0].value)}</div>
    </div>
  );
};

export default function OverchargeChart({ data, title, subtitle }: Props) {
  return (
    <div className="card" style={{ padding: '20px 20px 16px' }}>
      {title && (
        <div style={{ marginBottom: 16 }}>
          <div className="section-title">{title}</div>
          {subtitle && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{subtitle}</div>}
        </div>
      )}
      {data.length === 0 ? (
        <div className="empty-state" style={{ padding: 36 }}><div className="empty-sub">No data yet</div></div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
            <defs>
              <linearGradient id="orangeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F57921" />
                <stop offset="100%" stopColor="#F57921" stopOpacity={0.5} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 13, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} tickFormatter={v => `₹${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} />
            <Tooltip content={<Tip />} cursor={{ fill: 'rgba(245,121,33,0.06)' }} />
            <Bar dataKey="overcharge" fill="url(#orangeGrad)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
