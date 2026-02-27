'use client';
import { useEffect, useState } from 'react';
import { getAnalytics, formatINR } from '@/lib/api';
import KPICard from '@/components/KPICard';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#F59E0B','#EF4444','#6366F1','#10B981','#3B82F6','#EC4899','#8B5CF6'];
const CL: Record<string,string> = {
  rate_deviation:'Rate Dev', fuel_surcharge_mismatch:'Fuel', cod_fee_mismatch:'COD',
  rto_overcharge:'RTO', non_contracted_surcharge:'Unlisted', gst_miscalculation:'GST',
  arithmetic_total_mismatch:'Arithmetic', duplicate_awb:'Duplicate',
};
const CD: Record<string,string> = {
  rate_deviation:'Base freight above contracted zone rate',
  fuel_surcharge_mismatch:'Fuel % above contracted rate',
  cod_fee_mismatch:'COD fee exceeds contracted %',
  rto_overcharge:'Return freight above 50% of base',
  non_contracted_surcharge:'Surcharge not in rate card',
  gst_miscalculation:'GST on inflated base amount',
  arithmetic_total_mismatch:'Row total ≠ sum of components',
  duplicate_awb:'AWB billed more than once',
};

const Tip = ({active,payload,label}:any) => {
  if(!active||!payload?.length)return null;
  return <div style={{background:'var(--surface-2)',border:'1px solid var(--border-2)',borderRadius:8,padding:'10px 14px',fontSize:12,boxShadow:'var(--shadow-md)'}}>
    <div style={{fontWeight:600,color:'var(--text-primary)',marginBottom:4}}>{label}</div>
    {payload.map((p:any,i:number)=><div key={i} style={{color:p.color,fontFamily:'var(--font-mono)',fontSize:11}}>{p.name}: {typeof p.value==='number'&&p.value>100?formatINR(p.value):p.value}</div>)}
  </div>;
};

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  useEffect(()=>{getAnalytics().then(r=>setData(r.data)).catch(()=>{});},[]);

  if(!data) return <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:300,color:'var(--text-dim)',fontFamily:'var(--font-mono)',fontSize:12}}>Loading analytics…</div>;

  const totalDisc=data.check_type_totals?.reduce((s:number,c:any)=>s+c.count,0)??0;
  const avgPerInv=data.total_invoices>0?data.total_overcharge/data.total_invoices:0;
  const avgPerBatch=data.total_batches>0?data.total_overcharge/data.total_batches:0;
  const hitRate=data.total_invoices>0?(totalDisc/data.total_invoices*100):0;
  const rate=data.avg_overcharge_rate;
  const top=data.check_type_totals?.[0];
  const topProv=[...(data.provider_scorecards||[])].sort((a:any,b:any)=>b.overcharge-a.overcharge)[0];

  const pieData=(data.check_type_totals||[]).slice(0,7).map((c:any)=>({name:CL[c.check_type]||c.check_type,value:Math.round(c.overcharge)}));
  const barData=(data.check_type_totals||[]).map((c:any)=>({name:CL[c.check_type]||c.check_type,Freq:c.count,Overcharge:Math.round(c.overcharge)}));
  const providers=[...(data.provider_scorecards||[])].sort((a:any,b:any)=>b.overcharge-a.overcharge);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-sub">Cross-batch intelligence · violation trends · provider risk</p>
        </div>
      </div>

      <div className="kpi-grid-4">
        <KPICard label="Total Recoverable" value={formatINR(data.total_overcharge)} sub={`${data.total_batches} audits`} accent="amber" />
        <KPICard label="Overcharge Rate" value={`${rate}%`} sub="avg across all batches" accent={rate>10?'red':rate>5?'amber':'green'} />
        <KPICard label="Avg / Invoice" value={formatINR(avgPerInv)} sub="per shipment" accent="red" />
        <KPICard label="Hit Rate" value={`${hitRate.toFixed(1)}%`} sub={`${totalDisc} violations`} accent="blue" />
      </div>
      <div className="kpi-grid-4">
        <KPICard label="Avg / Batch" value={formatINR(avgPerBatch)} sub="per audit run" />
        <KPICard label="Top Violation" value={top?(CL[top.check_type]||top.check_type):'—'} sub={top?`${formatINR(top.overcharge)} · ${top.count} hits`:'no data'} accent="red" />
        <KPICard label="Highest Risk" value={topProv?.provider||'—'} sub={topProv?`${formatINR(topProv.overcharge)}`:'no data'} accent="amber" />
        <KPICard label="Checks Active" value={`${data.check_type_totals?.length??0} / ${Object.keys(CL).length}`} sub="violation categories" />
      </div>

      <div className="kpi-grid-2">
        <div className="card" style={{padding:'18px 18px 14px'}}>
          <div style={{marginBottom:14}}>
            <div className="section-title">Frequency vs Impact</div>
            <div style={{fontSize:11,color:'var(--text-dim)',marginTop:2}}>High frequency + high value = highest priority</div>
          </div>
          {barData.length>0?(
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} layout="vertical" margin={{left:0,right:40}}>
                <CartesianGrid strokeDasharray="2 6" horizontal={false}/>
                <XAxis type="number" tick={{fontSize:9,fill:'var(--text-dim)',fontFamily:'var(--font-mono)'}} axisLine={false} tickLine={false}/>
                <YAxis type="category" dataKey="name" tick={{fontSize:10,fill:'var(--text-secondary)',fontFamily:'var(--font-mono)'}} width={80} axisLine={false} tickLine={false}/>
                <Tooltip content={<Tip/>} cursor={{fill:'rgba(245,158,11,0.04)'}}/>
                <Legend iconType="circle" iconSize={6} wrapperStyle={{fontSize:10,color:'var(--text-muted)'}}/>
                <Bar dataKey="Freq" fill="url(#purpleGrad2)" radius={[0,3,3,0]}/>
                <Bar dataKey="Overcharge" fill="var(--purple)" radius={[0,3,3,0]}/>
              </BarChart>
            </ResponsiveContainer>
          ):<div className="empty-state" style={{padding:40}}><div className="empty-sub">No data yet</div></div>}
        </div>

        <div className="card" style={{padding:'18px 18px 14px'}}>
          <div style={{marginBottom:14}}>
            <div className="section-title">Overcharge Distribution</div>
            <div style={{fontSize:11,color:'var(--text-dim)',marginTop:2}}>Which violation costs the most money</div>
          </div>
          {pieData.length>0?(
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="46%" innerRadius={52} outerRadius={80} dataKey="value" paddingAngle={3}>
                  {pieData.map((_:any,i:number)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
                </Pie>
                <Tooltip formatter={(v:any)=>formatINR(v)} contentStyle={{background:'var(--surface-2)',border:'1px solid var(--border-2)',borderRadius:8,fontSize:11}}/>
                <Legend iconType="circle" iconSize={6} wrapperStyle={{fontSize:10,color:'var(--text-muted)'}}/>
              </PieChart>
            </ResponsiveContainer>
          ):<div className="empty-state" style={{padding:40}}><div className="empty-sub">No data yet</div></div>}
        </div>
      </div>

      {/* Violation table */}
      <div className="card" style={{marginBottom:16}}>
        <div className="card-header">
          <div><div className="section-title">Violation Breakdown</div><div style={{fontSize:11,color:'var(--text-dim)',marginTop:2}}>Every check type with impact and share</div></div>
        </div>
        {data.check_type_totals?.length>0?(
          <table className="data-table">
            <thead><tr><th>Violation</th><th>Description</th><th className="right">Hits</th><th className="right">Total Impact</th><th className="right">Avg / Hit</th><th>Share</th></tr></thead>
            <tbody>
              {data.check_type_totals.map((ct:any,i:number)=>{
                const pct=data.total_overcharge>0?(ct.overcharge/data.total_overcharge*100).toFixed(1):'0';
                const avg=ct.count>0?ct.overcharge/ct.count:0;
                return(
                  <tr key={ct.check_type}>
                    <td style={{fontWeight:600,color:'var(--text-primary)',whiteSpace:'nowrap'}}>{CL[ct.check_type]||ct.check_type}</td>
                    <td style={{fontSize:11,color:'var(--text-dim)',maxWidth:200}}>{CD[ct.check_type]||'—'}</td>
                    <td className="right"><span className="mono" style={{fontSize:11,fontWeight:600}}>{ct.count}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:11,fontWeight:600,color:'var(--orange)'}}>{formatINR(ct.overcharge)}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:11,color:'var(--text-muted)'}}>{formatINR(avg)}</span></td>
                    <td>
                      <div style={{display:'flex',alignItems:'center',gap:8}}>
                        <div style={{flex:1,height:4,background:'var(--surface-2)',borderRadius:99,minWidth:60,overflow:'hidden'}}>
                          <div style={{width:`${pct}%`,height:'100%',background:COLORS[i%COLORS.length],borderRadius:99,transition:'width 0.6s var(--ease)'}}/>
                        </div>
                        <span className="mono" style={{fontSize:10,color:'var(--text-dim)',minWidth:32}}>{pct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ):<div className="empty-state"><div className="empty-sub">No data yet</div></div>}
      </div>

      {/* Provider scorecard */}
      <div className="card">
        <div className="card-header">
          <div><div className="section-title">Provider Risk Scorecard</div><div style={{fontSize:11,color:'var(--text-dim)',marginTop:2}}>Ranked by total recoverable overcharge</div></div>
        </div>
        {providers.length>0?(
          <table className="data-table">
            <thead><tr><th>Rank</th><th>Provider</th><th className="right">Audits</th><th className="right">Invoices</th><th className="right">Violations</th><th className="right">Total Overcharge</th><th className="right">Per Invoice</th><th>Risk</th></tr></thead>
            <tbody>
              {providers.map((p:any,i:number)=>{
                const perInv=p.invoices>0?p.overcharge/p.invoices:0;
                const risk=perInv>200?{t:'HIGH',c:'var(--red)',b:'rgba(239,68,68,0.1)',bd:'rgba(239,68,68,0.2)'}:perInv>50?{t:'MED',c:'var(--orange)',b:'rgba(245,158,11,0.1)',bd:'rgba(245,158,11,0.2)'}:{t:'LOW',c:'var(--green)',b:'rgba(16,185,129,0.1)',bd:'rgba(16,185,129,0.2)'};
                return(
                  <tr key={p.provider}>
                    <td><span className="mono" style={{fontSize:11,color:'var(--text-dim)',fontWeight:600}}>#{i+1}</span></td>
                    <td style={{fontWeight:600,color:'var(--text-primary)',fontSize:12}}>{p.provider}</td>
                    <td className="right"><span className="mono" style={{fontSize:11}}>{p.batches}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:11}}>{p.invoices}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:11,fontWeight:600,color:'var(--red)'}}>{p.discrepancies}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:12,fontWeight:700,color:'var(--orange)'}}>{formatINR(p.overcharge)}</span></td>
                    <td className="right"><span className="mono" style={{fontSize:11,color:'var(--text-muted)'}}>{formatINR(perInv)}</span></td>
                    <td><span className="badge" style={{background:risk.b,color:risk.c,border:`1px solid ${risk.bd}`}}>{risk.t}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ):<div className="empty-state"><div className="empty-sub">No provider data yet</div></div>}
      </div>
    </div>
  );
}
