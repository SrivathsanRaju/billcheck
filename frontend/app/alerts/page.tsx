'use client';
import { useEffect, useState } from 'react';
import { getAlerts, markAlertRead, markAllAlertsRead } from '@/lib/api';
import Link from 'next/link';
import toast from 'react-hot-toast';

const SEV: Record<string,{bar:string;bg:string;ic:string;text:string}> = {
  critical: {bar:'var(--red)',   bg:'rgba(239,68,68,0.06)',  ic:'rgba(239,68,68,0.15)',  text:'var(--red)'},
  high:     {bar:'var(--orange)', bg:'rgba(245,158,11,0.05)', ic:'rgba(245,158,11,0.12)', text:'var(--orange)'},
  medium:   {bar:'var(--blue)',  bg:'rgba(59,130,246,0.04)', ic:'rgba(59,130,246,0.12)', text:'var(--blue)'},
  low:      {bar:'var(--green)', bg:'rgba(16,185,129,0.04)', ic:'rgba(16,185,129,0.12)', text:'var(--green)'},
};
const ICONS: Record<string,string> = {
  high_overcharge_rate:'↑%', moderate_overcharge_rate:'△', large_absolute_overcharge:'₹',
  multiple_critical:'!!', duplicate_awbs:'×2',
};

function ago(d:string):string {
  const m=Math.floor((Date.now()-new Date(d).getTime())/60000);
  if(m<1)return'just now'; if(m<60)return`${m}m ago`;
  const h=Math.floor(m/60); if(h<24)return`${h}h ago`;
  return`${Math.floor(h/24)}d ago`;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [filter, setFilter] = useState<'all'|'unread'>('all');

  const load = async () => { try { const r=await getAlerts(); setAlerts(r.data); } catch {} };
  useEffect(()=>{load();},[]);

  const handleRead = async (id:number) => { try { await markAlertRead(id); setAlerts(p=>p.map(a=>a.id===id?{...a,is_read:true}:a)); } catch {} };
  const handleReadAll = async () => { try { await markAllAlertsRead(); setAlerts(p=>p.map(a=>({...a,is_read:true}))); toast.success('All marked read'); } catch {} };

  const displayed = filter==='unread'?alerts.filter(a=>!a.is_read):alerts;
  const unread = alerts.filter(a=>!a.is_read).length;
  const critical = alerts.filter(a=>a.severity==='critical'&&!a.is_read).length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Alerts</h1>
          <p className="page-sub">
            {unread>0?`${unread} unread`:'All caught up'}
            {critical>0&&<span style={{color:'var(--red)',fontWeight:600}}> · {critical} critical</span>}
          </p>
        </div>
        <div className="page-header-actions">
          <div style={{display:'flex',background:'var(--surface-2)',borderRadius:6,padding:2,gap:1,border:'1px solid var(--border)'}}>
            {(['all','unread']as const).map(f=>(
              <button key={f} onClick={()=>setFilter(f)} style={{padding:'4px 12px',borderRadius:4,border:'none',cursor:'pointer',fontSize:11,fontWeight:600,fontFamily:'var(--font-body)',background:filter===f?'var(--surface-2)':'transparent',color:filter===f?'var(--text-primary)':'var(--text-dim)',transition:'all var(--dur) var(--ease)'}}>
                {f==='all'?'All':`Unread${unread>0?` (${unread})`:''}`}
              </button>
            ))}
          </div>
          {unread>0&&<button className="btn btn-secondary btn-sm" onClick={handleReadAll}>Mark all read</button>}
        </div>
      </div>

      {critical>0&&filter!=='unread'&&(
        <div style={{background:'rgba(239,68,68,0.08)',border:'1px solid rgba(239,68,68,0.2)',borderRadius:'var(--r-md)',padding:'10px 14px',marginBottom:14,display:'flex',alignItems:'center',gap:8}}>
          <span style={{width:6,height:6,borderRadius:'50%',background:'var(--red)',boxShadow:'0 0 8px var(--red)',display:'inline-block',flexShrink:0}}/>
          <span style={{fontSize:12,color:'var(--red)',fontWeight:500}}>{critical} critical alert{critical!==1?'s':''} require immediate attention</span>
        </div>
      )}

      <div style={{display:'flex',flexDirection:'column',gap:8}}>
        {displayed.length===0?(
          <div className="card"><div className="empty-state">
            <div className="empty-icon">🔔</div>
            <div className="empty-title">{filter==='unread'?'All caught up':'No alerts yet'}</div>
            <div className="empty-sub">{filter==='unread'?'No unread alerts':'Alerts appear after each audit run'}</div>
          </div></div>
        ):displayed.map(alert=>{
          const cfg=SEV[alert.severity]||SEV.medium;
          const icon=ICONS[alert.alert_type]||'!';
          return(
            <div key={alert.id} style={{
              background:alert.is_read?'var(--surface)':cfg.bg,
              border:'1px solid var(--border)',
              borderLeft:`3px solid ${alert.is_read?'var(--border-2)':cfg.bar}`,
              borderRadius:'var(--r-md)', padding:'14px 16px',
              display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:12,
              opacity:alert.is_read?0.6:1,
              transition:'all var(--dur) var(--ease)',
            }}>
              <div style={{display:'flex',gap:12,flex:1,minWidth:0}}>
                <div style={{width:32,height:32,borderRadius:6,flexShrink:0,background:alert.is_read?'var(--surface-2)':cfg.ic,color:alert.is_read?'var(--text-dim)':cfg.text,display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'var(--font-mono)',fontWeight:700,fontSize:11,letterSpacing:'0.02em'}}>
                  {icon}
                </div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:3}}>
                    <span style={{fontWeight:600,fontSize:13,color:alert.is_read?'var(--text-muted)':'var(--text-primary)'}}>{alert.title}</span>
                    {!alert.is_read&&<span style={{width:5,height:5,borderRadius:'50%',background:cfg.bar,display:'inline-block',flexShrink:0}}/>}
                  </div>
                  <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:8,lineHeight:1.5}}>{alert.message}</div>
                  <div style={{display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
                    <span className="badge" style={{background:alert.is_read?'var(--surface-2)':cfg.ic,color:alert.is_read?'var(--text-dim)':cfg.text,border:`1px solid ${alert.is_read?'var(--border)':cfg.bar+'44'}`}}>{alert.severity}</span>
                    {alert.batch_id&&<Link href={`/batches/${alert.batch_id}`} className="mono" style={{fontSize:10,color:'var(--orange)',textDecoration:'none',fontWeight:600}}>#{alert.batch_id}</Link>}
                    {alert.provider_name&&<span style={{fontSize:11,color:'var(--text-dim)'}}>{alert.provider_name}</span>}
                    <span className="mono" style={{fontSize:10,color:'var(--text-dim)'}}>{ago(alert.created_at)}</span>
                  </div>
                </div>
              </div>
              {!alert.is_read&&(
                <button className="btn btn-ghost btn-sm" onClick={()=>handleRead(alert.id)} style={{fontSize:11,flexShrink:0}}>Dismiss</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
