'use client';
import { useEffect, useState, useCallback } from 'react';
import { getBatch, getBatchReport, formatINR } from '@/lib/api';
import { StatusBadge } from '@/components/Badges';
import DiscrepancyTable from '@/components/DiscrepancyTable';
import DownloadButtons from '@/components/DownloadButtons';
import UploadPanel from '@/components/UploadPanel';
import KPICard from '@/components/KPICard';
import Link from 'next/link';

const AUDIT_STEPS = [
  'Reading invoice file…',
  'Detecting provider…',
  'Parsing line items…',
  'Loading rate contract…',
  'Running 7 compliance checks…',
  'Checking for duplicate AWBs…',
  'Computing overcharge amounts…',
  'Finalising report…',
];

function AuditingSpinner({ step }: { step: number }) {
  return (
    <div style={{ padding: '40px 20px', textAlign: 'center' }}>
      {/* Animated rings */}
      <div style={{ position: 'relative', width: 80, height: 80, margin: '0 auto 24px' }}>
        <div style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          border: '3px solid var(--border-2)',
          borderTopColor: 'var(--orange)',
          animation: 'spin 0.9s linear infinite',
        }} />
        <div style={{
          position: 'absolute', inset: 10, borderRadius: '50%',
          border: '2px solid var(--border)',
          borderBottomColor: 'var(--purple-bright)',
          animation: 'spin 1.4s linear infinite reverse',
        }} />
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color: 'var(--orange)',
        }}>
          ✓
        </div>
      </div>

      <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 8 }}>
        Auditing in progress
      </div>
      <div key={step} style={{
        fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--orange)',
        animation: 'fadeInUp 0.4s ease',
      }}>
        {AUDIT_STEPS[step % AUDIT_STEPS.length]}
      </div>

      {/* Progress dots */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 20 }}>
        {AUDIT_STEPS.map((_, i) => (
          <div key={i} style={{
            width: i <= step ? 6 : 4,
            height: i <= step ? 6 : 4,
            borderRadius: '50%',
            background: i <= step ? 'var(--orange)' : 'var(--border-2)',
            transition: 'all 0.3s ease',
            marginTop: i <= step ? 0 : 1,
          }} />
        ))}
      </div>
    </div>
  );
}

export default function UploadPage() {
  const [batchId, setBatchId] = useState<number | null>(null);
  const [batch, setBatch] = useState<any>(null);
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);
  const [polling, setPolling] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);

  const pollBatch = useCallback(async (id: number) => {
    try {
      const r = await getBatch(id);
      setBatch(r.data);
      if (r.data.status === 'completed') {
        setPolling(false);
        const rep = await getBatchReport(id);
        setDiscrepancies(rep.data.discrepancies || []);
      } else if (r.data.status === 'failed') {
        setPolling(false);
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (!batchId || !polling) return;
    const iv = setInterval(() => pollBatch(batchId), 2000);
    return () => clearInterval(iv);
  }, [batchId, polling, pollBatch]);

  // Cycle through step messages while auditing
  useEffect(() => {
    if (!polling) return;
    const iv = setInterval(() => setStepIdx(i => i + 1), 1200);
    return () => clearInterval(iv);
  }, [polling]);

  const handleBatchCreated = (id: number) => {
    setBatchId(id);
    setPolling(true);
    setStepIdx(0);
    setBatch({ id, status: 'pending' });
    setDiscrepancies([]);
  };

  const s = batch?.summary;
  const isCompleted = batch?.status === 'completed';
  const isFailed = batch?.status === 'failed';
  const isProcessing = polling && !isCompleted && !isFailed;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Upload Invoice</h1>
          <p className="page-sub">Upload a courier invoice + rate contract to detect overcharges instantly</p>
        </div>
      </div>

      <UploadPanel onBatchCreated={handleBatchCreated} />

      {batchId && batch && (
        <div style={{ marginTop: 20 }} className="fade-in">

          {/* Processing state */}
          {isProcessing && (
            <div className="card" style={{ marginBottom: 16 }}>
              <AuditingSpinner step={stepIdx} />
            </div>
          )}

          {/* Failed state */}
          {isFailed && (
            <div className="card" style={{ padding: 24, marginBottom: 16, borderTop: '2px solid var(--red)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(255,71,87,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 18 }}>⚠️</div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--red)', marginBottom: 6 }}>Audit failed</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>{batch.error_message || 'An unexpected error occurred during processing.'}</div>
                  <button className="btn btn-secondary btn-sm" onClick={() => { setBatch(null); setBatchId(null); }}>Try again</button>
                </div>
              </div>
            </div>
          )}

          {/* Completed — result hero */}
          {isCompleted && s && (
            <>
              {/* Result hero banner */}
              <div style={{
                background: s.total_overcharge > 0
                  ? 'linear-gradient(135deg, rgba(245,121,33,0.1) 0%, rgba(71,47,145,0.1) 100%)'
                  : 'linear-gradient(135deg, rgba(0,196,140,0.08) 0%, rgba(0,196,140,0.04) 100%)',
                border: `1px solid ${s.total_overcharge > 0 ? 'rgba(245,121,33,0.25)' : 'rgba(0,196,140,0.25)'}`,
                borderRadius: 'var(--r-lg)',
                padding: '20px 24px',
                marginBottom: 18,
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                flexWrap: 'wrap',
              }}>
                <div style={{ fontSize: 36 }}>
                  {s.total_overcharge > 0 ? '🔍' : '✅'}
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {s.total_overcharge > 0
                      ? <>Found <span style={{ color: 'var(--orange)', fontFamily: 'var(--font-mono)' }}>{formatINR(s.total_overcharge)}</span> in overcharges</>
                      : 'All charges are compliant!'
                    }
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    {s.total_invoices} invoices audited · {s.total_discrepancies} violation{s.total_discrepancies !== 1 ? 's' : ''} found
                    {s.overcharge_rate > 0 && ` · ${s.overcharge_rate}% overcharge rate`}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Link href={`/batches/${batchId}`} className="btn btn-secondary btn-sm">
                    Full report →
                  </Link>
                  <DownloadButtons batchId={batchId} />
                </div>
              </div>

              <div className="kpi-grid-4" style={{ marginBottom: 16 }}>
                <KPICard label="Total Invoices" value={s.total_invoices} sub="Line items audited" />
                <KPICard label="Discrepancies" value={s.total_discrepancies} sub="Violations detected" accent={s.total_discrepancies > 0 ? 'red' : 'green'} />
                <KPICard label="Overcharge Found" value={formatINR(s.total_overcharge)} sub="Recoverable amount" accent="amber" />
                <KPICard label="Rate" value={`${s.overcharge_rate}%`} sub="Of total billed" accent={s.overcharge_rate > 10 ? 'red' : s.overcharge_rate > 5 ? 'amber' : 'green'} />
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="section-title">
                      {discrepancies.length > 0 ? `${discrepancies.length} Discrepancies Found` : 'No Discrepancies'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                      {discrepancies.length > 0 ? 'Click any row to expand · raise disputes below' : 'All charges match contracted rates — well done!'}
                    </div>
                  </div>
                </div>
                <DiscrepancyTable discrepancies={discrepancies} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
