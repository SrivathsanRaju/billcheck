'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getBatch, getBatchDisputes, updateDispute, bulkRaiseDisputes, formatINR } from '@/lib/api';
import { StatusBadge, SeverityBadge } from '@/components/Badges';
import KPICard from '@/components/KPICard';
import { KPIGridSkeleton, TableSkeleton, Skeleton } from '@/components/Skeleton';
import DownloadButtons from '@/components/DownloadButtons';
import DiscrepancyTable from '@/components/DiscrepancyTable';
import OverchargeChart from '@/components/OverchargeChart';
import Link from 'next/link';
import toast from 'react-hot-toast';

const CHECK_LABELS: Record<string, string> = {
  duplicate_awb: 'Duplicate AWB', weight_overcharge: 'Weight Pad',
  rate_deviation: 'Rate Dev', cod_fee_mismatch: 'COD Fee',
  rto_overcharge: 'RTO', fuel_surcharge_mismatch: 'Fuel',
  non_contracted_surcharge: 'Unlisted',
};

export default function BatchDetailPage() {
  const params = useParams();
  const batchId = Number(params.id);
  const [batch, setBatch] = useState<any>(null);
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [bRes, dRes] = await Promise.all([getBatch(batchId), getBatchDisputes(batchId)]);
      setBatch(bRes.data);
      setDiscrepancies(dRes.data || []);
    } catch {}
    finally { setLoading(false); }
  };
  useEffect(() => { loadData(); }, [batchId]);

  const handleUpdateDispute = async (id: number, status: string) => {
    try {
      await updateDispute(id, { dispute_status: status });
      setDiscrepancies(p => p.map(d => d.id === id ? { ...d, dispute_status: status } : d));
      toast.success('Updated');
    } catch { toast.error('Failed'); }
  };

  const handleBulkRaise = async () => {
    try {
      const r = await bulkRaiseDisputes(batchId);
      toast.success(`${r.data.raised} disputes raised`);
      loadData();
    } catch { toast.error('Failed'); }
  };

  if (loading) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <div>
            <Skeleton width={120} height={10} style={{ marginBottom: 8 }} />
            <Skeleton width={200} height={28} style={{ marginBottom: 6 }} />
            <Skeleton width={280} height={13} />
          </div>
        </div>
        <KPIGridSkeleton count={4} />
        <div className="kpi-grid-2" style={{ marginTop: 20 }}>
          <div className="card" style={{ padding: 20, height: 260 }}><Skeleton width="100%" height="100%" /></div>
          <div className="card" style={{ padding: 20, height: 260 }}><Skeleton width="100%" height="100%" /></div>
        </div>
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header"><Skeleton width={160} height={18} /></div>
          <TableSkeleton rows={6} cols={8} />
        </div>
      </div>
    );
  }

  if (!batch) return (
    <div className="empty-state" style={{ height: 300 }}>
      <div className="empty-icon">⚠️</div>
      <div className="empty-title">Batch not found</div>
      <Link href="/batches" className="btn btn-secondary" style={{ marginTop: 12 }}>← Back to batches</Link>
    </div>
  );

  const s = batch.summary || {};

  // Fix: properly compute check data from actual discrepancies (not summary counts)
  const checkDataMap: Record<string, number> = {};
  for (const d of discrepancies) {
    checkDataMap[d.check_type] = (checkDataMap[d.check_type] || 0) + (d.overcharge_amount || 0);
  }
  const checkData = Object.entries(checkDataMap)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({
      name: CHECK_LABELS[k] || k.replace(/_/g, ' '),
      overcharge: Math.round(v),
    }))
    .sort((a, b) => b.overcharge - a.overcharge);

  const pendingCount = discrepancies.filter(d => d.dispute_status === 'pending').length;
  const raisedCount = discrepancies.filter(d => d.dispute_status === 'raised').length;
  const resolvedCount = discrepancies.filter(d => d.dispute_status === 'resolved').length;
  const criticalCount = discrepancies.filter(d => d.severity === 'critical').length;
  const potentialRecovery = discrepancies.filter(d => d.dispute_status !== 'rejected').reduce((s, d) => s + d.overcharge_amount, 0);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Link href="/batches" style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', textDecoration: 'none', letterSpacing: '0.06em' }}>BATCHES</Link>
            <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>/</span>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-secondary)' }}>#{batchId}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <h1 className="page-title mono">Batch #{batchId}</h1>
            <StatusBadge status={batch.status} />
            {batch.provider_name && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 8px', fontFamily: 'var(--font-mono)' }}>
                {batch.provider_name}
              </span>
            )}
            {criticalCount > 0 && (
              <span style={{ fontSize: 11, color: 'var(--red)', background: 'rgba(255,71,87,0.1)', border: '1px solid rgba(255,71,87,0.2)', borderRadius: 4, padding: '2px 8px', fontFamily: 'var(--font-mono)', fontWeight: 600, letterSpacing: '0.04em' }}>
                {criticalCount} CRITICAL
              </span>
            )}
          </div>
          <p className="page-sub">{batch.invoice_file} · {new Date(batch.created_at).toLocaleString('en-IN')}</p>
        </div>
        <div className="page-header-actions">
          {pendingCount > 0 && (
            <button className="btn btn-secondary" onClick={handleBulkRaise}>
              Raise {pendingCount} pending
            </button>
          )}
          <DownloadButtons batchId={batchId} />
        </div>
      </div>

      {/* Recovery call-out banner */}
      {potentialRecovery > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(245,121,33,0.08) 0%, rgba(71,47,145,0.08) 100%)',
          border: '1px solid rgba(245,121,33,0.22)',
          borderRadius: 'var(--r-md)',
          padding: '14px 20px',
          marginBottom: 18,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(245,121,33,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F57921" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>
                <span style={{ color: 'var(--orange)', fontFamily: 'var(--font-mono)' }}>{formatINR(potentialRecovery)}</span> recoverable from {discrepancies.length} violation{discrepancies.length !== 1 ? 's' : ''}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                {raisedCount > 0 && `${raisedCount} raised · `}
                {resolvedCount > 0 && `${resolvedCount} resolved · `}
                {pendingCount > 0 && `${pendingCount} pending dispute`}
              </div>
            </div>
          </div>
          {pendingCount > 0 && (
            <button className="btn btn-primary" onClick={handleBulkRaise} style={{ fontSize: 13 }}>
              Raise all pending →
            </button>
          )}
        </div>
      )}

      <div className="kpi-grid-4">
        <KPICard label="Total Invoices" value={s.total_invoices || 0} sub="Audited" />
        <KPICard label="Discrepancies" value={s.total_discrepancies || 0} sub="Violations found" accent={(s.total_discrepancies || 0) > 0 ? 'red' : 'green'} />
        <KPICard label="Total Overcharge" value={formatINR(s.total_overcharge || 0)} sub="Recoverable" accent="amber" />
        <KPICard label="Overcharge Rate" value={`${s.overcharge_rate || 0}%`} sub="Of total billed" accent={(s.overcharge_rate || 0) > 10 ? 'red' : (s.overcharge_rate || 0) > 5 ? 'amber' : 'green'} />
      </div>

      <div className="kpi-grid-2">
        {checkData.length > 0 ? (
          <OverchargeChart data={checkData} title="Overcharge by Type" subtitle="Financial impact per violation category" />
        ) : (
          <div className="card" style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div className="empty-state">
              <div className="empty-icon" style={{ fontSize: 24 }}>✓</div>
              <div className="empty-title" style={{ color: 'var(--green)', fontSize: 15 }}>Clean batch</div>
              <div className="empty-sub">No overcharges detected</div>
            </div>
          </div>
        )}

        <div className="card" style={{ padding: 18 }}>
          <div className="section-title" style={{ marginBottom: 14 }}>Severity Breakdown</div>
          {Object.entries(s.severity_counts || {}).length > 0 ? (
            Object.entries(s.severity_counts || {}).map(([sev, cnt]: any) => (
              <div key={sev} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <SeverityBadge severity={sev} />
                <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{cnt}</span>
              </div>
            ))
          ) : (
            <div style={{ padding: '20px 0', color: 'var(--text-dim)', fontSize: 12, textAlign: 'center' }}>No violations</div>
          )}
          <div style={{ marginTop: 16 }}>
            <div className="label" style={{ marginBottom: 10 }}>Batch Info</div>
            {[
              ['Invoice', batch.invoice_file],
              ['Contract', batch.contract_file],
              ['Provider', batch.provider_name || '—'],
            ].map(([l, v]) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: 'var(--text-dim)' }}>{l}</span>
                <span className="mono" style={{ color: 'var(--text-muted)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-title">Discrepancies ({discrepancies.length})</div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
              {pendingCount > 0 ? `${pendingCount} pending · ` : ''}
              {raisedCount > 0 ? `${raisedCount} raised · ` : ''}
              {resolvedCount > 0 ? `${resolvedCount} resolved` : ''}
              {pendingCount === 0 && raisedCount === 0 && resolvedCount === 0 ? 'All tracked' : ''}
            </div>
          </div>
        </div>
        <DiscrepancyTable discrepancies={discrepancies} onUpdateDispute={handleUpdateDispute} />
      </div>
    </div>
  );
}
