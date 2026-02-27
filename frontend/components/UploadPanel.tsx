'use client';
import { useState, useRef, useEffect } from 'react';
import { uploadFiles, getContracts, deleteContract } from '@/lib/api';
import axios from 'axios';
import toast from 'react-hot-toast';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
interface SavedContract { id:number; name:string; provider:string; created_at:string; }
interface Props { onBatchCreated: (id:number) => void; }

function DropZone({ label, sublabel, file, onFile, accept }: { label:string; sublabel:string; file:File|null; onFile:(f:File)=>void; accept:string; }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const filled = !!file;
  return (
    <div
      onClick={() => ref.current?.click()}
      onDragOver={e=>{e.preventDefault();setDrag(true);}}
      onDragLeave={()=>setDrag(false)}
      onDrop={e=>{e.preventDefault();setDrag(false);const f=e.dataTransfer.files[0];if(f)onFile(f);}}
      style={{
        border: `1px dashed ${filled?'var(--green)':drag?'var(--orange)':'var(--border-2)'}`,
        borderRadius:'var(--r-md)', padding:'22px 18px',
        textAlign:'center', cursor:'pointer',
        background: filled?'rgba(16,185,129,0.06)':drag?'var(--orange-light)':'var(--surface-2)',
        transition:'all var(--dur) var(--ease)',
        display:'flex', flexDirection:'column', alignItems:'center', gap:8,
      }}
    >
      <input ref={ref} type="file" accept={accept} hidden onChange={e=>e.target.files&&onFile(e.target.files[0])} />
      {filled ? (
        <>
          <div style={{ width:32,height:32,borderRadius:'50%',background:'var(--green)',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--bg)',boxShadow:'0 0 12px rgba(16,185,129,0.3)' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <div style={{ fontFamily:'var(--font-mono)',fontSize:11,color:'var(--green)',fontWeight:500 }}>{file!.name}</div>
          <div style={{ fontSize:10,color:'var(--text-dim)' }}>{(file!.size/1024).toFixed(1)} KB · click to replace</div>
        </>
      ) : (
        <>
          <div style={{ color:'var(--text-dim)',opacity:0.5 }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
            </svg>
          </div>
          <div style={{ fontFamily:'var(--font-body)',fontSize:12,fontWeight:600,color:'var(--text-secondary)' }}>{label}</div>
          <div style={{ fontSize:11,color:'var(--text-dim)' }}>{sublabel}</div>
        </>
      )}
    </div>
  );
}

export default function UploadPanel({ onBatchCreated }: Props) {
  const [invoiceFile, setInvoiceFile] = useState<File|null>(null);
  const [contractFile, setContractFile] = useState<File|null>(null);
  const [mode, setMode] = useState<'upload'|'saved'>('upload');
  const [saved, setSaved] = useState<SavedContract[]>([]);
  const [selectedId, setSelectedId] = useState<number|null>(null);
  const [saveCheck, setSaveCheck] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveProv, setSaveProv] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchSaved = async () => { try { const r = await getContracts(); setSaved(r.data||[]); } catch {} };
  useEffect(() => { fetchSaved(); }, []);

  const contractReady = mode==='upload' ? !!contractFile : !!selectedId;
  const canSubmit = !!invoiceFile && contractReady && !loading;

  const handleDelete = async (id:number,e:React.MouseEvent) => {
    e.stopPropagation();
    try { await deleteContract(id); setSaved(p=>p.filter(c=>c.id!==id)); if(selectedId===id)setSelectedId(null); toast.success('Contract removed'); }
    catch { toast.error('Delete failed'); }
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    try {
      if (mode==='upload') {
        if (saveCheck&&saveName&&saveProv&&contractFile) {
          const fd=new FormData(); fd.append('name',saveName); fd.append('provider',saveProv); fd.append('contract_file',contractFile);
          await axios.post(`${BASE}/api/v1/contracts/save`,fd); await fetchSaved();
        }
        const fd=new FormData(); fd.append('invoice_file',invoiceFile!); fd.append('contract_file',contractFile!);
        const r=await uploadFiles(fd); onBatchCreated(r.data.batch_id);
      } else {
        const fd=new FormData(); fd.append('invoice_file',invoiceFile!); fd.append('saved_contract_id',String(selectedId));
        const r=await uploadFiles(fd); onBatchCreated(r.data.batch_id);
      }
      toast.success('Audit started');
    } catch(err:any) { toast.error(err?.response?.data?.detail||'Upload failed'); }
    finally { setLoading(false); }
  };

  const StepNum = ({ n, done }: { n:number; done:boolean }) => (
    <div style={{ width:22,height:22,borderRadius:'50%',background:done?'var(--green)':'var(--surface-3)',border:`1px solid ${done?'var(--green)':'var(--border-2)'}`,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,boxShadow:done?'0 0 8px rgba(16,185,129,0.25)':'none',transition:'all var(--dur) var(--ease)' }}>
      {done ? (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--bg)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      ) : (
        <span style={{ fontFamily:'var(--font-mono)',fontSize:10,color:'var(--text-muted)',fontWeight:600 }}>{n}</span>
      )}
    </div>
  );

  return (
    <div className="card" style={{ padding:24 }}>
      {/* Step 1 */}
      <div style={{ marginBottom:20 }}>
        <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:10 }}>
          <StepNum n={1} done={!!invoiceFile} />
          <span style={{ fontFamily:'var(--font-display)',fontWeight:600,fontSize:13,color:'var(--text-primary)' }}>Invoice File</span>
          <span style={{ fontFamily:'var(--font-mono)',fontSize:9,background:'rgba(239,68,68,0.1)',color:'var(--red)',border:'1px solid rgba(239,68,68,0.2)',padding:'1px 6px',borderRadius:3,letterSpacing:'0.06em' }}>REQUIRED</span>
        </div>
        <DropZone label="Drop invoice CSV or PDF" sublabel="All major carrier formats supported" file={invoiceFile} onFile={setInvoiceFile} accept=".csv,.pdf" />
      </div>

      <div className="divider" style={{ margin:'0 0 20px' }} />

      {/* Step 2 */}
      <div style={{ marginBottom:20 }}>
        <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:10 }}>
          <div style={{ display:'flex',alignItems:'center',gap:8 }}>
            <StepNum n={2} done={contractReady} />
            <span style={{ fontFamily:'var(--font-display)',fontWeight:600,fontSize:13,color:'var(--text-primary)' }}>Rate Contract</span>
            <span style={{ fontFamily:'var(--font-mono)',fontSize:9,background:'rgba(239,68,68,0.1)',color:'var(--red)',border:'1px solid rgba(239,68,68,0.2)',padding:'1px 6px',borderRadius:3,letterSpacing:'0.06em' }}>REQUIRED</span>
          </div>
          <div style={{ display:'flex',background:'var(--surface-2)',borderRadius:6,padding:2,gap:1,border:'1px solid var(--border)' }}>
            {(['upload','saved'] as const).map(m=>(
              <button key={m} onClick={()=>setMode(m)} style={{ padding:'4px 12px',borderRadius:4,border:'none',cursor:'pointer',fontSize:11,fontWeight:600,fontFamily:'var(--font-body)',background:mode===m?'var(--surface-3)':'transparent',color:mode===m?'var(--text-primary)':'var(--text-dim)',transition:'all var(--dur) var(--ease)' }}>
                {m==='upload'?'Upload New':`Saved (${saved.length})`}
              </button>
            ))}
          </div>
        </div>

        {mode==='upload' ? (
          <>
            <DropZone label="Drop rate contract CSV or PDF" sublabel="Freight slabs, surcharge rates, GST" file={contractFile} onFile={setContractFile} accept=".csv,.pdf" />
            {contractFile && (
              <div style={{ marginTop:10,padding:'10px 12px',background:'var(--surface-2)',borderRadius:'var(--r-md)',border:'1px solid var(--border)' }}>
                <label style={{ display:'flex',alignItems:'center',gap:8,cursor:'pointer' }}>
                  <input type="checkbox" checked={saveCheck} onChange={e=>setSaveCheck(e.target.checked)} style={{ width:13,height:13,accentColor:'var(--orange)',cursor:'pointer' }} />
                  <span style={{ fontSize:12,color:'var(--text-secondary)' }}>Save contract for future audits</span>
                </label>
                {saveCheck && (
                  <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,marginTop:10 }}>
                    <div>
                      <div className="label" style={{ marginBottom:5 }}>Contract name</div>
                      <input className="input" value={saveName} onChange={e=>setSaveName(e.target.value)} placeholder="e.g. BlueDart Q1 2025" style={{ fontSize:12 }} />
                    </div>
                    <div>
                      <div className="label" style={{ marginBottom:5 }}>Provider</div>
                      <input className="input" value={saveProv} onChange={e=>setSaveProv(e.target.value)} placeholder="e.g. BlueDart" style={{ fontSize:12 }} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        ) : saved.length===0 ? (
          <div style={{ padding:'24px',textAlign:'center',border:'1px dashed var(--border)',borderRadius:'var(--r-md)',background:'var(--surface-2)' }}>
            <div style={{ fontSize:12,color:'var(--text-dim)',marginBottom:8 }}>No saved contracts yet</div>
            <button className="btn btn-ghost btn-sm" onClick={()=>setMode('upload')}>Upload one →</button>
          </div>
        ) : (
          <div style={{ display:'flex',flexDirection:'column',gap:6 }}>
            {saved.map(c=>(
              <div key={c.id} onClick={()=>setSelectedId(c.id===selectedId?null:c.id)}
                style={{ display:'flex',alignItems:'center',justifyContent:'space-between',padding:'10px 12px',borderRadius:'var(--r-md)',cursor:'pointer',border:`1px solid ${selectedId===c.id?'var(--orange)':'var(--border)'}`,background:selectedId===c.id?'rgba(245,121,33,0.1)':'var(--surface-2)',transition:'all var(--dur) var(--ease)' }}>
                <div style={{ display:'flex',alignItems:'center',gap:10 }}>
                  <div style={{ width:8,height:8,borderRadius:'50%',flexShrink:0,border:`2px solid ${selectedId===c.id?'var(--orange)':'var(--border-2)'}`,background:selectedId===c.id?'var(--orange)':'transparent',transition:'all var(--dur) var(--ease)' }} />
                  <div>
                    <div style={{ fontSize:12,fontWeight:600,color:selectedId===c.id?'var(--orange)':'var(--text-primary)' }}>{c.name}</div>
                    <div style={{ fontFamily:'var(--font-mono)',fontSize:10,color:'var(--text-dim)',marginTop:1 }}>{c.provider} · {new Date(c.created_at).toLocaleDateString('en-IN')}</div>
                  </div>
                </div>
                <button onClick={e=>handleDelete(c.id,e)} className="btn btn-ghost btn-sm" style={{ fontSize:11,color:'var(--text-dim)' }}>Remove</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submit */}
      {(!invoiceFile||!contractReady) && (
        <div style={{ fontSize:11,color:'var(--text-dim)',marginBottom:10,fontFamily:'var(--font-mono)' }}>
          {!invoiceFile && <span style={{ color:'var(--red)',marginRight:12 }}>· invoice required</span>}
          {!contractReady && <span style={{ color:'var(--red)' }}>· contract required</span>}
        </div>
      )}
      <button className="btn btn-primary btn-full btn-lg" onClick={handleSubmit} disabled={!canSubmit}>
        {loading ? (
          <><span className="pulse" style={{ width:7,height:7,borderRadius:'50%',background:'var(--surface-2)',display:'inline-block' }} />Processing audit…</>
        ) : (
          <>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            Run Billing Audit
          </>
        )}
      </button>
    </div>
  );
}
