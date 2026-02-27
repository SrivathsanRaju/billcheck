'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getBatch, getBatchDisputes, updateDispute, bulkRaiseDisputes, formatINR } from '@/lib/api';
import { StatusBadge, SeverityBadge } from '@/components/Badges';
import KPICard from '@/components/KPICard';
import DownloadButtons from '@/components/DownloadButtons';
import DiscrepancyTable from '@/components/DiscrepancyTable';
import OverchargeChart from '@/components/OverchargeChart';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function BatchDetailPage() {
  const params = useParams();
  const batchId = Number(params.id);
  const [batch, setBatch] = useState<any>(null);
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);

  const loadData = async () => {
    try {
      const [bRes,dRes] = await Promise.all([getBatch(batchId), getBatchDisputes(batchId)]);
      setBatch(bRes.data); setDiscrepancies(dRes.data||[]);
    } catch {}
  };
  useEffect(()=>{loadData();},[batchId]);

  const handleUpdateDispute = async (id:number,status:string) => {
    try { await updateDispute(id,{dispute_status:status}); setDiscrepancies(p=>p.map(d=>d.id===id?{...d,dispute_status:status}:d)); toast.success('Updated'); }
    catch { toast.error('Failed'); }
  };
  const handleBulkRaise = async () => {
    try { const r=await bulkRaiseDisputes(batchId); toast.success(`${r.data.raised} disputes raised`); loadData(); }
    catch { toast.error('Failed'); }
  };

  if (!batch) return <div style={{ display:'flex',alignItems:'center',justifyContent:'center',height:300,color:'var(--text-dim)',fontFamily:'var(--font-mono)',fontSize:12 }}>Loading…</div>;

  const s = batch.summary||{};
  const checkData = Object.entries(s.check_type_counts||{}).map(([k]:any)=>({
    name: k.replace(/_/g,' '),
    overcharge: discrepancies.filter(d=>d.check_type===k).reduce((sum:number,d:any)=>sum+d.overcharge_amount,0),
  }));
  const pendingCount = discrepancies.filter(d=>d.dispute_status==='pending').length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:6 }}>
            <Link href="/batches" style={{ fontFamily:'var(--font-mono)',fontSize:10,color:'var(--text-dim)',textDecoration:'none',letterSpacing:'0.06em' }}>BATCHES</Link>
            <span style={{ color:'var(--border-2)',fontSize:12 }}>/</span>
            <span className="mono" style={{ fontSize:10,color:'var(--text-muted)' }}>#{batchId}</span>
          </div>
          <div style={{ display:'flex',alignItems:'center',gap:10 }}>
            <h1 className="page-title mono">Batch #{batchId}</h1>
            <StatusBadge status={batch.status} />
            {batch.provider_name && <span style={{ fontSize:12,color:'var(--text-muted)' }}>{batch.provider_name}</span>}
          </div>
          <p className="page-sub">{batch.invoice_file} · {new Date(batch.created_at).toLocaleString('en-IN')}</p>
        </div>
        <div className="page-header-actions">
          {pendingCount>0 && <button className="btn btn-secondary" onClick={handleBulkRaise}>Raise {pendingCount} pending</button>}
          <DownloadButtons batchId={batchId} />
        </div>
      </div>

      <div className="kpi-grid-4">
        <KPICard label="Total Invoices" value={s.total_invoices||0} sub="Audited" />
        <KPICard label="Discrepancies" value={s.total_discrepancies||0} sub="Violations" accent={(s.total_discrepancies||0)>0?'red':'green'} />
        <KPICard label="Total Overcharge" value={formatINR(s.total_overcharge||0)} sub="Recoverable" accent="amber" />
        <KPICard label="Overcharge Rate" value={`${s.overcharge_rate||0}%`} sub="Of billed" accent={(s.overcharge_rate||0)>10?'red':(s.overcharge_rate||0)>5?'amber':'green'} />
      </div>

      <div className="kpi-grid-2">
        <OverchargeChart data={checkData} title="Overcharge by Type" subtitle="Financial impact per violation category" />
        <div className="card" style={{ padding:18 }}>
          <div className="section-title" style={{ marginBottom:14 }}>Severity Breakdown</div>
          {Object.entries(s.severity_counts||{}).map(([sev,cnt]:any)=>(
            <div key={sev} style={{ display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:'1px solid var(--border)' }}>
              <SeverityBadge severity={sev} />
              <span className="mono" style={{ fontSize:12,fontWeight:600,color:'var(--text-primary)' }}>{cnt}</span>
            </div>
          ))}
          <div style={{ marginTop:16 }}>
            <div className="label" style={{ marginBottom:10 }}>Batch Info</div>
            {[['Invoice',batch.invoice_file],['Contract',batch.contract_file],['Provider',batch.provider_name||'—']].map(([l,v])=>(
              <div key={l} style={{ display:'flex',justifyContent:'space-between',marginBottom:6,fontSize:12 }}>
                <span style={{ color:'var(--text-dim)' }}>{l}</span>
                <span className="mono" style={{ color:'var(--text-muted)',maxWidth:160,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:11 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-title">Discrepancies ({discrepancies.length})</div>
            <div style={{ fontSize:11,color:'var(--text-dim)',marginTop:2 }}>{pendingCount>0?`${pendingCount} pending disputes`:'All tracked'}</div>
          </div>
        </div>
        <DiscrepancyTable discrepancies={discrepancies} onUpdateDispute={handleUpdateDispute} />
      </div>
    </div>
  );
}
