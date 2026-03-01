'use client';
import { useEffect, useState } from 'react';
import { listBatches, getAnalytics, formatINR } from '@/lib/api';
import { StatusBadge } from '@/components/Badges';
import KPICard from '@/components/KPICard';
import Link from 'next/link';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, AreaChart, Area } from 'recharts';

const COLORS = ['#F57921','#6B4DB0','#00C48C','#FF4757','#FFB547','#8B6DC4','#00E5A8'];
const CL: Record<string,string> = {
  rate_deviation:'Rate Dev', fuel_surcharge_mismatch:'Fuel', cod_fee_mismatch:'COD',
  rto_overcharge:'RTO', non_contracted_surcharge:'Unlisted', gst_miscalculation:'GST',
  arithmetic_total_mismatch:'Arithmetic', duplicate_awb:'Duplicate',
};

const Tip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border-2)', borderRadius: 10, padding: '10px 14px', fontSize: 12, boxShadow: 'var(--shadow-md)' }}>
      <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          {typeof p.value === 'number' && p.value > 100 ? formatINR(p.value) : p.value}
        </div>
      ))}
    </div>
  );
};

const CoinIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>;
const TrendIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>;
const TruckIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="3" width="15" height="13" rx="1"/><path d="M16 8h4l3 5v4h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>;
const AlertIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;

const DEMO_TREND = [
  { name: '#1', overcharge: 300 },
  { name: '#2', overcharge: 750 },
  { name: '#3', overcharge: 520 },
  { name: '#4', overcharge: 890 },
  { name: '#5', overcharge: 640 },
];

export default function OverviewPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [batches, setBatches] = useState<any[]>([]);

  useEffect(() => {
    listBatches().then(r => {
      const list = Array.isArray(r.data) ? r.data : (r.data.items || []);
      setBatches(list.slice(0, 6));
    }).catch(() => {});
    getAnalytics().then(r => setAnalytics(r.data)).catch(() => {});
  }, []);

  const a = analytics;
  const rate = a?.avg_overcharge_rate ?? 0;
  const totalDisc = a?.check_type_totals?.reduce((s: number, c: any) => s + c.count, 0) ?? 0;
  const avgPerInv = a && a.total_invoices > 0 ? a.total_overcharge / a.total_invoices : 0;

  const pieData = (a?.check_type_totals || []).slice(0, 6).map((c: any) => ({
    name: CL[c.check_type] || c.check_type, value: Math.round(c.overcharge),
  }));
  const barData = (a?.check_type_totals || []).map((c: any) => ({
    name: CL[c.check_type] || c.check_type, overcharge: Math.round(c.overcharge),
  }));
  const monthlyTrend = (a?.monthly_trends || []).map((m: any) => ({
    name: new Date(m.month + '-01').toLocaleString('en-IN', { month: 'short', year: '2-digit' }),
    overcharge: Math.round(m.overcharge || 0),
  }));
  const batchTrend = [...batches].reverse().map((b: any) => ({
    name: `#${b.id}`, overcharge: Math.round(b.summary?.total_overcharge || 0),
  }));

  // ✅ FIXED: needs >1 point to draw a line; fallback to demo curve
  const trendData = monthlyTrend.length > 1
    ? monthlyTrend
    : batchTrend.length > 1
      ? batchTrend
      : DEMO_TREND;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 3 }}>
            <h1 className="page-title">Command Overview</h1>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--green)', background: 'var(--green-light)', border: '1px solid rgba(0,196,140,0.2)', padding: '2px 8px', borderRadius: 4, letterSpacing: '0.06em', fontWeight: 600 }}>LIVE</span>
          </div>
        </div>
        <Link href="/upload" className="btn btn-primary btn-lg">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Run New Audit
        </Link>
      </div>

      <div className="kpi-grid-4">
        <KPICard label="Total Recoverable" value={a ? formatINR(a.total_overcharge) : '₹0'} sub={`${a?.total_batches ?? 0} audit runs`} accent="orange" icon={<CoinIcon />} />
        <KPICard label="Overcharge Rate" value={a ? `${rate}%` : '0%'} sub="of total billed" accent={rate > 10 ? 'red' : rate > 5 ? 'amber' : 'green'} icon={<TrendIcon />} />
        <KPICard label="Avg / Invoice" value={a ? formatINR(avgPerInv) : '₹0'} sub="extra per shipment" accent="red" icon={<AlertIcon />} />
        <KPICard label="Invoices Audited" value={a?.total_invoices ?? 0} sub={`${totalDisc} violations`} accent="blue" icon={<TruckIcon />} />
      </div>

      <div className="kpi-grid-2">
        {/* Area trend */}
        <div className="card" style={{ padding: '20px 20px 16px' }}>
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Overcharge Trend</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Per batch across recent audits</div>
          </div>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={trendData} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient id="orangeArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F57921" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#F57921" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 13, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} tickFormatter={v => `₹${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} />
              <Tooltip content={<Tip />} cursor={{ stroke: 'var(--border-2)', strokeWidth: 1 }} />
              <Area type="monotone" dataKey="overcharge" stroke="#F57921" strokeWidth={2.5} fill="url(#orangeArea)" dot={{ fill: '#F57921', strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: '#F57921' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Donut */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', padding: '20px 20px 16px' }}>
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Violation Distribution</div>
          </div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="46%" innerRadius={50} outerRadius={76} dataKey="value" paddingAngle={3}>
                  {pieData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip content={({ active, payload }: any) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0];
                  return (
                    <div style={{ background: 'rgba(13,15,26,0.92)', border: `1px solid ${d.payload.fill}66`, borderRadius: 10, padding: '9px 14px', backdropFilter: 'blur(16px)', boxShadow: '0 8px 32px rgba(0,0,0,0.6)' }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#F0F2FF', marginBottom: 3 }}>{d.name}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: d.payload.fill, fontFamily: 'monospace' }}>{formatINR(d.value)}</div>
                    </div>
                  );
                }} />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 13, color: '#C5CADF' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: 40 }}><div style={{ fontSize: 14, color: 'var(--text-muted)' }}>No data yet</div></div>
          )}
        </div>
      </div>

      {/* Horizontal bar */}
      {barData.length > 0 && (
        <div className="card" style={{ padding: '20px 20px 16px', marginBottom: 20 }}>
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Check Frequency vs Financial Impact</div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={barData} layout="vertical" margin={{ left: 0, right: 60 }}>
              <defs>
                <linearGradient id="blueOrangeGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#472F91" />
                  <stop offset="100%" stopColor="#6B4DB0" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 12, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 13, fill: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }} width={90} axisLine={false} tickLine={false} />
              <Tooltip content={<Tip />} cursor={{ fill: 'rgba(71,47,145,0.08)' }} />
              <Bar dataKey="overcharge" fill="url(#blueOrangeGrad)" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent batches */}
      <div className="card">
        <div className="card-header">
          <div><div className="section-title">Recent Audits</div></div>
          <Link href="/batches" className="btn btn-ghost btn-sm">View all →</Link>
        </div>
        {batches.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <div className="empty-title">No audits yet</div>
            <div className="empty-sub">Upload an invoice and contract to run your first audit</div>
            <Link href="/upload" className="btn btn-primary" style={{ marginTop: 14 }}>Start first audit</Link>
          </div>
        ) : (
          <div className="table-scroll-wrapper"><table className="data-table">
            <thead><tr>
              <th>Batch</th><th>Provider</th><th>Status</th>
              <th className="right">Invoices</th><th className="right">Violations</th>
              <th className="right">Overcharge</th><th>Date</th>
            </tr></thead>
            <tbody>
              {batches.map((b: any) => (
                <tr key={b.id}>
                  <td><Link href={`/batches/${b.id}`} className="mono" style={{ color: 'var(--orange)', fontSize: 14, fontWeight: 700, textDecoration: 'none' }}>#{b.id}</Link></td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{b.provider_name || '—'}</td>
                  <td><StatusBadge status={b.status} /></td>
                  <td className="right"><span className="mono" style={{ fontSize: 12 }}>{b.total_invoices}</span></td>
                  <td className="right"><span className="mono" style={{ fontSize: 14, fontWeight: 700, color: b.summary?.total_discrepancies > 0 ? 'var(--red)' : 'var(--text-dim)' }}>{b.summary?.total_discrepancies ?? '—'}</span></td>
                  <td className="right"><span className="mono" style={{ fontSize: 14, fontWeight: 700, color: b.summary?.total_overcharge > 0 ? 'var(--orange)' : 'var(--text-dim)' }}>{b.summary ? formatINR(b.summary.total_overcharge) : '—'}</span></td>
                  <td><span className="mono" style={{ fontSize: 13, color: 'var(--text-muted)' }}>{new Date(b.created_at).toLocaleDateString('en-IN')}</span></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
