'use client';
import { useEffect, useState, useCallback } from 'react';
import { getBatch, getBatchReport, formatINR } from '@/lib/api';
import { StatusBadge } from '@/components/Badges';
import DiscrepancyTable from '@/components/DiscrepancyTable';
import DownloadButtons from '@/components/DownloadButtons';
import UploadPanel from '@/components/UploadPanel';
import KPICard from '@/components/KPICard';

export default function UploadPage() {
  const [batchId, setBatchId] = useState<number|null>(null);
  const [batch, setBatch] = useState<any>(null);
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);
  const [polling, setPolling] = useState(false);

  const pollBatch = useCallback(async (id:number) => {
    try {
      const r = await getBatch(id); setBatch(r.data);
      if (r.data.status==='completed') { setPolling(false); const rep=await getBatchReport(id); setDiscrepancies(rep.data.discrepancies||[]); }
      else if (r.data.status==='failed') setPolling(false);
    } catch {}
  }, []);

  useEffect(() => {
    if (!batchId||!polling) return;
    const iv = setInterval(()=>pollBatch(batchId),2000);
    return ()=>clearInterval(iv);
  }, [batchId,polling,pollBatch]);

  const handleBatchCreated = (id:number) => { setBatchId(id); setPolling(true); setBatch({id,status:'pending'}); setDiscrepancies([]); };
  const s = batch?.summary;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Upload Invoice</h1>
          <p className="page-sub">Run an automated audit against your contracted rates</p>
        </div>
      </div>

      <UploadPanel onBatchCreated={handleBatchCreated} />

      {batchId && batch && (
        <div style={{ marginTop:20 }}>
          {/* Status bar */}
          <div className="card" style={{ padding:'12px 18px',marginBottom:16,display:'flex',alignItems:'center',gap:12,background:'var(--surface-2)' }}>
            <div style={{ fontFamily:'var(--font-mono)',fontSize:10,color:'var(--text-dim)',letterSpacing:'0.06em' }}>BATCH</div>
            <span className="mono" style={{ fontSize:12,color:'var(--orange)',fontWeight:600 }}>#{batchId}</span>
            <StatusBadge status={batch.status} />
            {polling && (
              <span style={{ fontSize:11,color:'var(--text-dim)',display:'flex',alignItems:'center',gap:6 }}>
                <span className="pulse" style={{ width:5,height:5,borderRadius:'50%',background:'var(--orange)',display:'inline-block' }} />
                Auditing line items…
              </span>
            )}
            {batch.status==='completed' && <span style={{ fontSize:11,color:'var(--green)',fontWeight:500 }}>Audit complete</span>}
            {batch.status==='failed' && <span style={{ fontSize:11,color:'var(--red)' }}>Failed: {batch.error_message}</span>}
          </div>

          {s && (
            <>
              <div className="kpi-grid-4" style={{ marginBottom:16 }}>
                <KPICard label="Total Invoices" value={s.total_invoices} sub="Line items audited" />
                <KPICard label="Discrepancies" value={s.total_discrepancies} sub="Violations detected" accent={s.total_discrepancies>0?'red':'green'} />
                <KPICard label="Overcharge Found" value={formatINR(s.total_overcharge)} sub="Recoverable amount" accent="amber" />
                <KPICard label="Rate" value={`${s.overcharge_rate}%`} sub="Of total billed" accent={s.overcharge_rate>10?'red':s.overcharge_rate>5?'amber':'green'} />
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="section-title">{discrepancies.length>0?`${discrepancies.length} Discrepancies Found`:'No Discrepancies'}</div>
                    <div style={{ fontSize:11,color:'var(--text-dim)',marginTop:2 }}>{discrepancies.length>0?'Review and raise disputes below':'All charges match contracted rates'}</div>
                  </div>
                  {discrepancies.length>0 && <DownloadButtons batchId={batchId} />}
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
