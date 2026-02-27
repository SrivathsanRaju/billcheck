'use client';
import { SeverityBadge, StatusBadge } from './Badges';
import { formatINR } from '@/lib/api';

interface Discrepancy {
  id: number; awb_number: string; check_type: string; description: string;
  billed_value: number|null; expected_value: number|null;
  overcharge_amount: number; severity: string; confidence_score: number; dispute_status: string;
}
interface Props { discrepancies: Discrepancy[]; onUpdateDispute?: (id: number, status: string) => void; }

const CHECK_LABELS: Record<string,string> = {
  duplicate_awb:'Duplicate AWB', weight_overcharge:'Weight Overcharge',
  zone_mismatch:'Zone Mismatch', rate_deviation:'Rate Deviation',
  cod_fee_mismatch:'COD Fee', rto_overcharge:'RTO Overcharge',
  fuel_surcharge_mismatch:'Fuel Surcharge', non_contracted_surcharge:'Unlisted Charge',
  gst_miscalculation:'GST Error', arithmetic_total_mismatch:'Arithmetic Error',
};

export default function DiscrepancyTable({ discrepancies, onUpdateDispute }: Props) {
  if (!discrepancies.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✓</div>
        <div className="empty-title" style={{ color: 'var(--green)' }}>No discrepancies</div>
        <div className="empty-sub">All line items match contracted rates</div>
      </div>
    );
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>AWB</th><th>Violation</th><th>Severity</th>
            <th className="right">Billed</th><th className="right">Expected</th>
            <th className="right">Overcharge</th><th className="right">Conf.</th><th>Dispute</th>
          </tr>
        </thead>
        <tbody>
          {discrepancies.map(d => (
            <tr key={d.id}>
              <td>
                <span className="mono" style={{ fontSize: 13, color: 'var(--orange)', fontWeight: 500 }}>
                  {d.awb_number}
                </span>
              </td>
              <td>
                <div style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: 12 }}>
                  {CHECK_LABELS[d.check_type] || d.check_type}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 2, maxWidth: 220, lineHeight: 1.4 }}>
                  {d.description}
                </div>
              </td>
              <td><SeverityBadge severity={d.severity} /></td>
              <td className="right">
                <span className="mono" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  {d.billed_value != null ? formatINR(d.billed_value) : '—'}
                </span>
              </td>
              <td className="right">
                <span className="mono" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  {d.expected_value != null ? formatINR(d.expected_value) : '—'}
                </span>
              </td>
              <td className="right">
                <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--orange)' }}>
                  {formatINR(d.overcharge_amount)}
                </span>
              </td>
              <td className="right">
                <span className="mono" style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                  {(d.confidence_score * 100).toFixed(0)}%
                </span>
              </td>
              <td>
                {onUpdateDispute ? (
                  <select value={d.dispute_status} onChange={e => onUpdateDispute(d.id, e.target.value)}
                    style={{ background: 'var(--surface-2)', border: '1px solid var(--border-2)', borderRadius: 4, padding: '4px 8px', fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                    {['pending','raised','acknowledged','resolved','rejected'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                ) : <StatusBadge status={d.dispute_status} />}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
