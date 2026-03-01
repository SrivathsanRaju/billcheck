'use client';
import { useEffect, useState } from 'react';
import { listBatches, deleteBatch, formatINR } from '@/lib/api';
import { StatusBadge } from '@/components/Badges';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function BatchesPage() {
  const [batches, setBatches] = useState<any[]>([]);
  const load = async () => { try { const r=await listBatches(); setBatches(r.data); } catch {} };
  useEffect(()=>{load();},[]);

  const handleDelete = async (id:number) => {
    if (!confirm(`Delete batch #${id}?`)) return;
    try { await deleteBatch(id); toast.success('Batch deleted'); load(); }
    catch { toast.error('Delete failed'); }
  };

  const totalOC = batches.reduce((s,b)=>s+(b.summary?.total_overcharge||0),0);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Batch History</h1>
          <p className="page-sub">{batches.length} audits · {formatINR(totalOC)} total recoverable</p>
        </div>
        <Link href="/upload" className="btn btn-primary">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Audit
        </Link>
      </div>

      <div className="card">
        {batches.length===0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <div className="empty-title">No batches yet</div>
            <div className="empty-sub">Upload an invoice to run your first audit</div>
            <Link href="/upload" className="btn btn-primary" style={{ marginTop:12 }}>Start now</Link>
          </div>
        ) : (
          <div className="table-scroll-wrapper"><table className="data-table">
            <thead><tr>
              <th>Batch</th><th>Invoice File</th><th>Provider</th><th>Status</th>
              <th className="right">Invoices</th><th className="right">Violations</th>
              <th className="right">Overcharge</th><th>Date</th><th></th>
            </tr></thead>
            <tbody>
              {batches.map((b:any)=>(
                <tr key={b.id}>
                  <td><Link href={`/batches/${b.id}`} className="mono" style={{ color:'var(--orange)',fontSize:11,fontWeight:600,textDecoration:'none' }}>#{b.id}</Link></td>
                  <td><div style={{ maxWidth:160,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-muted)' }}>{b.invoice_file}</div></td>
                  <td style={{ color:'var(--text-primary)',fontWeight:500,fontSize:12 }}>{b.provider_name||'—'}</td>
                  <td><StatusBadge status={b.status} /></td>
                  <td className="right"><span className="mono" style={{ fontSize:11 }}>{b.total_invoices}</span></td>
                  <td className="right"><span className="mono" style={{ fontSize:11,fontWeight:b.summary?.total_discrepancies>0?600:400,color:b.summary?.total_discrepancies>0?'var(--red)':'var(--text-dim)' }}>{b.summary?.total_discrepancies??'—'}</span></td>
                  <td className="right"><span className="mono" style={{ fontSize:11,fontWeight:600,color:b.summary?.total_overcharge>0?'var(--orange)':'var(--text-dim)' }}>{b.summary?formatINR(b.summary.total_overcharge):'—'}</span></td>
                  <td><span className="mono" style={{ fontSize:10,color:'var(--text-dim)' }}>{new Date(b.created_at).toLocaleDateString('en-IN')}</span></td>
                  <td>
                    <div style={{ display:'flex',gap:4 }}>
                      <Link href={`/batches/${b.id}`} className="btn btn-ghost btn-sm">View</Link>
                      <button onClick={()=>handleDelete(b.id)} className="btn btn-danger btn-sm">Del</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
