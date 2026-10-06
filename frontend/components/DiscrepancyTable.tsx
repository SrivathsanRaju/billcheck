'use client';
import { useState } from 'react';
import { SeverityBadge, StatusBadge } from './Badges';
import { formatINR } from '@/lib/api';

interface Discrepancy {
  id: number; awb_number: string; check_type: string; description: string;
  billed_value: number | null; expected_value: number | null;
  overcharge_amount: number; severity: string; confidence_score: number;
  dispute_status: string; confidence_reason?: string;
}
interface Props {
  discrepancies: Discrepancy[];
  onUpdateDispute?: (id: number, status: string) => void;
}

const CHECK_LABELS: Record<string, string> = {
  duplicate_awb: 'Duplicate AWB', weight_overcharge: 'Weight Overcharge',
  zone_mismatch: 'Zone Mismatch', rate_deviation: 'Rate Deviation',
  cod_fee_mismatch: 'COD Fee', rto_overcharge: 'RTO Overcharge',
  fuel_surcharge_mismatch: 'Fuel Surcharge', non_contracted_surcharge: 'Unlisted Charge',
  gst_miscalculation: 'GST Error', arithmetic_total_mismatch: 'Arithmetic Error',
};

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

type SortKey = 'severity' | 'overcharge' | 'confidence' | 'default';
type FilterConf = 'all' | 'high' | 'medium';

function ConfidenceDot({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? 'var(--green)' : pct >= 70 ? 'var(--orange)' : 'var(--text-dim)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5, justifyContent: 'flex-end' }}>
      <div style={{ width: 28, height: 4, background: 'var(--surface-2)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99, transition: 'width 0.5s ease' }} />
      </div>
      <span className="mono" style={{ fontSize: 11, color, minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

export default function DiscrepancyTable({ discrepancies, onUpdateDispute }: Props) {
  const [sort, setSort] = useState<SortKey>('default');
  const [confFilter, setConfFilter] = useState<FilterConf>('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (!discrepancies.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✓</div>
        <div className="empty-title" style={{ color: 'var(--green)' }}>No discrepancies</div>
        <div className="empty-sub">All line items match contracted rates</div>
      </div>
    );
  }

  let filtered = discrepancies.filter(d => {
    if (confFilter === 'high') return d.confidence_score >= 0.9;
    if (confFilter === 'medium') return d.confidence_score >= 0.7 && d.confidence_score < 0.9;
    return true;
  });

  if (sort === 'severity') filtered = [...filtered].sort((a, b) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9));
  else if (sort === 'overcharge') filtered = [...filtered].sort((a, b) => b.overcharge_amount - a.overcharge_amount);
  else if (sort === 'confidence') filtered = [...filtered].sort((a, b) => b.confidence_score - a.confidence_score);

  const totalShown = filtered.reduce((s, d) => s + d.overcharge_amount, 0);

  return (
    <div>
      {/* Filter / sort toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 20px', borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4, background: 'var(--surface-2)', borderRadius: 6, padding: 2, border: '1px solid var(--border)' }}>
          {(['all', 'high', 'medium'] as FilterConf[]).map(f => (
            <button key={f} onClick={() => setConfFilter(f)} style={{
              padding: '3px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
              fontSize: 11, fontWeight: 600, fontFamily: 'var(--font-mono)',
              background: confFilter === f ? 'var(--surface-3)' : 'transparent',
              color: confFilter === f ? 'var(--text-primary)' : 'var(--text-dim)',
              transition: 'all 0.15s ease',
            }}>
              {f === 'all' ? 'All' : f === 'high' ? '≥90% conf.' : '70-90%'}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 4, background: 'var(--surface-2)', borderRadius: 6, padding: 2, border: '1px solid var(--border)' }}>
          {([['default', 'Default'], ['severity', 'Severity'], ['overcharge', 'Impact ↓'], ['confidence', 'Conf ↓']] as [SortKey, string][]).map(([k, label]) => (
            <button key={k} onClick={() => setSort(k)} style={{
              padding: '3px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
              fontSize: 11, fontWeight: 600, fontFamily: 'var(--font-mono)',
              background: sort === k ? 'var(--surface-3)' : 'transparent',
              color: sort === k ? 'var(--text-primary)' : 'var(--text-dim)',
              transition: 'all 0.15s ease',
            }}>
              {label}
            </button>
          ))}
        </div>

        <span className="mono" style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 'auto' }}>
          {filtered.length} of {discrepancies.length} · {formatINR(totalShown)} shown
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>AWB</th>
              <th>Violation</th>
              <th>Severity</th>
              <th className="right">Billed</th>
              <th className="right">Expected</th>
              <th className="right">Overcharge</th>
              <th className="right">Confidence</th>
              <th>Dispute</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(d => (
              <>
                <tr key={d.id} style={{ cursor: 'pointer' }} onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}>
                  <td>
                    <span className="mono" style={{ fontSize: 12, color: 'var(--orange)', fontWeight: 600 }}>
                      {d.awb_number}
                    </span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 12 }}>
                      {CHECK_LABELS[d.check_type] || d.check_type}
                    </div>
                  </td>
                  <td><SeverityBadge severity={d.severity} /></td>
                  <td className="right">
                    <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {d.billed_value != null ? formatINR(d.billed_value) : '—'}
                    </span>
                  </td>
                  <td className="right">
                    <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {d.expected_value != null ? formatINR(d.expected_value) : '—'}
                    </span>
                  </td>
                  <td className="right">
                    <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--orange)' }}>
                      {formatINR(d.overcharge_amount)}
                    </span>
                  </td>
                  <td className="right">
                    <ConfidenceDot score={d.confidence_score} />
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    {onUpdateDispute ? (
                      <select
                        value={d.dispute_status}
                        onChange={e => onUpdateDispute(d.id, e.target.value)}
                        style={{ background: 'var(--surface-2)', border: '1px solid var(--border-2)', borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}
                      >
                        {['pending', 'raised', 'acknowledged', 'resolved', 'rejected'].map(s => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    ) : <StatusBadge status={d.dispute_status} />}
                  </td>
                </tr>
                {expandedId === d.id && (
                  <tr key={`${d.id}-detail`} style={{ background: 'rgba(245,121,33,0.03)' }}>
                    <td colSpan={8} style={{ padding: '10px 20px 14px' }}>
                      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                        <div style={{ flex: 2, minWidth: 200 }}>
                          <div className="label" style={{ marginBottom: 5 }}>Description</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>{d.description}</div>
                        </div>
                        {d.confidence_reason && (
                          <div style={{ flex: 1, minWidth: 160 }}>
                            <div className="label" style={{ marginBottom: 5 }}>Confidence Reason</div>
                            <div style={{ fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.6 }}>{d.confidence_reason}</div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
